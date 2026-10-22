from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

import httpx

from backend.feige.database import connect, utc_now
from backend.feige.domain import SuggestionItem, SuggestionView
from backend.feige.services.knowledge import KnowledgeService


class ModelNotConfigured(RuntimeError):
    pass


class ModelOutputError(RuntimeError):
    pass


class RiskBlocked(RuntimeError):
    pass


class ModelGateway:
    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        model: str,
        api_key: str,
    ) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def generate(self, messages: list[dict]) -> str:
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
            },
            timeout=30,
        )
        response.raise_for_status()
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelOutputError("模型响应结构无效") from exc


class SuggestionService:
    def __init__(
        self,
        db_path: Path,
        knowledge_service: KnowledgeService,
        model_gateway: ModelGateway | None = None,
    ) -> None:
        self.db_path = db_path
        self.knowledge_service = knowledge_service
        self.model_gateway = model_gateway

    def generate(self, conversation_id: str, trigger: str) -> SuggestionView:
        gateway = self.model_gateway or self._gateway_from_settings()
        if gateway is None:
            raise ModelNotConfigured("请先在设置中配置大模型")

        with connect(self.db_path) as connection:
            conversation = connection.execute(
                """
                SELECT cv.*, c.name AS customer_name, o.order_no,
                    oi.product_id, p.category, p.title AS product_title
                FROM conversations cv
                JOIN customers c ON c.id = cv.customer_id
                LEFT JOIN orders o ON o.id = cv.order_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN products p ON p.id = oi.product_id
                WHERE cv.id = ?
                LIMIT 1
                """,
                (conversation_id,),
            ).fetchone()
            if not conversation:
                raise ValueError("会话不存在")
            messages = connection.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY sent_at",
                (conversation_id,),
            ).fetchall()

        latest_buyer = next(
            (
                message["content"]
                for message in reversed(messages)
                if message["role"] == "buyer"
            ),
            "",
        )
        hits = self.knowledge_service.retrieve(
            latest_buyer,
            product_id=conversation["product_id"],
            category=conversation["category"],
            limit=5,
        )
        context_summary = (
            f"客户：{conversation['customer_name']}；订单：{conversation['order_no'] or '无'}；"
            f"商品：{conversation['product_title'] or '未关联'}；"
            f"买家问题：{latest_buyer or '无'}"
        )
        knowledge_text = "\n".join(
            f"[{hit.title}] {hit.snippet}" for hit in hits
        ) or "未命中知识库"
        dialogue_text = "\n".join(
            f"{message['role']}: {message['content']}" for message in messages[-20:]
        )
        prompt = (
            "你是服装店客服的回复建议助手。只能提供参考话术，不能声称已经替客户"
            "退款、改单或发货，不能提供站外联系方式。输出严格 JSON，必须包含三条"
            "风格分别为专业说明、简洁直接、温和安抚的建议。\n"
            f"业务上下文：\n{context_summary}\n"
            f"知识库：\n{knowledge_text}\n"
            f"会话：\n{dialogue_text}"
        )
        content = gateway.generate(
            [
                {
                    "role": "system",
                    "content": "你是只读客服辅助助手，最终消息必须由客服人工审核。",
                },
                {"role": "user", "content": prompt},
            ]
        )
        parsed = self._parse_model_output(content)
        allowed_styles = ["专业说明", "简洁直接", "温和安抚"]
        items = [SuggestionItem.model_validate(item) for item in parsed]
        if [item.style for item in items] != allowed_styles:
            raise ModelOutputError("模型未返回规定的三条建议")

        warnings = self._sensitive_warnings(items)
        status = "blocked" if warnings else "success"
        suggestion_id = str(uuid4())
        now = utc_now()
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO suggestions VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL
                )
                """,
                (
                    suggestion_id,
                    conversation_id,
                    context_summary,
                    gateway.model,
                    status,
                    json.dumps([item.model_dump() for item in items], ensure_ascii=False),
                    json.dumps(warnings, ensure_ascii=False),
                    trigger,
                    now,
                ),
            )
            for rank, hit in enumerate(hits, start=1):
                connection.execute(
                    """
                    INSERT INTO suggestion_sources VALUES (?, ?, ?, ?, NULL, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        suggestion_id,
                        str(hit.entry_id),
                        str(hit.product_id) if hit.product_id else None,
                        hit.title,
                        rank,
                    ),
                )
            connection.execute(
                "INSERT INTO analytics_events VALUES (?, 'suggestion_generated', ?, ?)",
                (
                    str(uuid4()),
                    json.dumps({"suggestion_id": suggestion_id, "trigger": trigger}),
                    now,
                ),
            )
            if warnings:
                connection.execute(
                    "INSERT INTO analytics_events VALUES (?, 'suggestion_blocked', ?, ?)",
                    (
                        str(uuid4()),
                        json.dumps({"suggestion_id": suggestion_id, "warnings": warnings}),
                        now,
                    ),
                )
        return self.get(suggestion_id)

    def get(self, suggestion_id: str) -> SuggestionView:
        suggestion_id = str(suggestion_id)
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM suggestions WHERE id = ?",
                (suggestion_id,),
            ).fetchone()
            if not row:
                raise ValueError("建议不存在")
            return self._to_view(connection, row)

    def list_for_conversation(self, conversation_id: str) -> list[SuggestionView]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM suggestions
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                """,
                (conversation_id,),
            ).fetchall()
            return [self._to_view(connection, row) for row in rows]

    def track_copy(self, suggestion_id: str) -> dict:
        suggestion_id = str(suggestion_id)
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM suggestions WHERE id = ?",
                (suggestion_id,),
            ).fetchone()
            if not row:
                raise ValueError("建议不存在")
            if row["status"] == "blocked":
                raise RiskBlocked("风险建议禁止复制")
            now = utc_now()
            connection.execute(
                """
                UPDATE suggestions SET copied_count = copied_count + 1,
                    last_copied_at = ?
                WHERE id = ?
                """,
                (now, suggestion_id),
            )
            connection.execute(
                "INSERT INTO analytics_events VALUES (?, 'suggestion_copied', ?, ?)",
                (
                    str(uuid4()),
                    json.dumps({"suggestion_id": suggestion_id}),
                    now,
                ),
            )
            count = row["copied_count"] + 1
        return {"ok": True, "copied_count": count, "sent_to_buyer": False}

    def test_connection(self) -> dict:
        gateway = self.model_gateway or self._gateway_from_settings()
        if gateway is None:
            raise ModelNotConfigured("请先保存模型配置")
        preview = gateway.generate(
            [{"role": "user", "content": "只回复：连接成功"}]
        )
        return {"ok": True, "preview": preview[:120]}

    def _gateway_from_settings(self) -> ModelGateway | None:
        with connect(self.db_path) as connection:
            settings = {
                row["key"]: row["value"]
                for row in connection.execute(
                    """
                    SELECT key, value FROM app_settings
                    WHERE key IN ('model_base_url', 'model_name', 'model_api_key')
                    """
                )
            }
        if not all(
            settings.get(key)
            for key in ("model_base_url", "model_name", "model_api_key")
        ):
            return None
        return ModelGateway(
            httpx.Client(),
            settings["model_base_url"],
            settings["model_name"],
            settings["model_api_key"],
        )

    def _parse_model_output(self, content: str) -> list[dict]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            payload = json.loads(cleaned)
            suggestions = payload["suggestions"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ModelOutputError("模型输出不是有效的建议 JSON") from exc
        if not isinstance(suggestions, list) or len(suggestions) != 3:
            raise ModelOutputError("模型必须返回三条建议")
        return suggestions

    def _sensitive_warnings(self, items: list[SuggestionItem]) -> list[str]:
        warnings: list[str] = []
        for item in items:
            text = re.sub(r"\s+", "", item.text).lower()
            if "微信" in text or "wechat" in text or "vx" in text:
                warnings.append("offsite_contact")
            if "qq" in text:
                warnings.append("offsite_contact")
            if re.search(r"1[3-9]\d{9}", text):
                warnings.append("phone_number")
            if re.search(r"https?://|www\.", text):
                warnings.append("offsite_link")
        return sorted(set(warnings))

    def _to_view(self, connection, row) -> SuggestionView:
        sources = [
            {
                "knowledge_id": source["knowledge_id"],
                "title": source["title"],
                "product_id": source["product_id"],
                "sku_id": source["sku_id"],
                "rank": source["rank"],
            }
            for source in connection.execute(
                "SELECT * FROM suggestion_sources WHERE suggestion_id = ? ORDER BY rank",
                (row["id"],),
            ).fetchall()
        ]
        return SuggestionView(
            id=row["id"],
            conversation_id=row["conversation_id"],
            status=row["status"],
            trigger=row["trigger_type"],
            suggestions=json.loads(row["suggestions_json"]),
            sources=sources,
            warnings=json.loads(row["warnings_json"]),
            model_name=row["model_name"],
            created_at=row["created_at"],
            copied_count=row["copied_count"],
        )
