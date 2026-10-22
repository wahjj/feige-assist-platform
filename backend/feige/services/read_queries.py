from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from backend.feige.database import connect


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


class ReadQueries:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def list_products(self, query: str = "", category: str = "") -> list[dict]:
        clauses = ["1 = 1"]
        params: list[str] = []
        if query:
            like = f"%{query}%"
            clauses.append(
                """(
                    p.title LIKE ? OR p.category LIKE ? OR
                    EXISTS (
                        SELECT 1 FROM product_skus s
                        WHERE s.product_id = p.id
                        AND (s.sku_name LIKE ? OR s.size LIKE ?)
                    )
                )"""
            )
            params.extend([like, like, like, like])
        if category:
            clauses.append("p.category = ?")
            params.append(category)
        with connect(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT p.*,
                    EXISTS(
                        SELECT 1 FROM knowledge_entries k
                        WHERE k.product_id = p.id AND k.enabled = 1
                    ) AS knowledge_bound
                FROM products p
                WHERE {' AND '.join(clauses)}
                ORDER BY p.synced_at DESC, p.title
                """,
                params,
            ).fetchall()
            return [self._product_summary(connection, row) for row in rows]

    def product_detail(self, product_id: str) -> dict:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT p.*,
                    EXISTS(
                        SELECT 1 FROM knowledge_entries k
                        WHERE k.product_id = p.id AND k.enabled = 1
                    ) AS knowledge_bound
                FROM products p WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="商品不存在")
            return self._product_summary(connection, row, include_skus=True)

    def _product_summary(
        self,
        connection,
        row,
        include_skus: bool = True,
    ) -> dict:
        skus = connection.execute(
            "SELECT * FROM product_skus WHERE product_id = ? ORDER BY size, color",
            (row["id"],),
        ).fetchall()
        payload = dict(row)
        payload["knowledge_bound"] = bool(payload["knowledge_bound"])
        if include_skus:
            payload["skus"] = [dict(sku) for sku in skus]
        else:
            payload["sku_count"] = len(skus)
            payload["sizes"] = sorted({sku["size"] for sku in skus if sku["size"]})
        return payload

    def list_orders(self, query: str = "") -> list[dict]:
        params: list[str] = []
        where = ""
        if query:
            like = f"%{query}%"
            where = """
                WHERE o.order_no LIKE ? OR c.name LIKE ? OR EXISTS (
                    SELECT 1 FROM order_items oi
                    WHERE oi.order_id = o.id AND oi.product_name LIKE ?
                )
            """
            params = [like, like, like]
        with connect(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT o.*, c.name AS customer_name,
                    (SELECT SUM(quantity) FROM order_items WHERE order_id = o.id)
                        AS item_count
                FROM orders o JOIN customers c ON c.id = o.customer_id
                {where}
                ORDER BY o.created_at DESC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def order_detail(self, order_id: str) -> dict:
        with connect(self.db_path) as connection:
            order = connection.execute(
                """
                SELECT o.*, c.name AS customer_name, c.external_id AS customer_external_id
                FROM orders o JOIN customers c ON c.id = o.customer_id
                WHERE o.id = ?
                """,
                (order_id,),
            ).fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")
            items = connection.execute(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY id",
                (order_id,),
            ).fetchall()
        return {**dict(order), "items": [dict(item) for item in items]}

    def list_customers(self, query: str = "", tag: str = "") -> list[dict]:
        params: list[str] = []
        clauses = ["1 = 1"]
        if query:
            like = f"%{query}%"
            clauses.append("(c.name LIKE ? OR c.phone LIKE ?)")
            params.extend([like, like])
        if tag:
            clauses.append("a.tags_json LIKE ?")
            params.append(f"%{tag}%")
        with connect(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT c.*, COALESCE(a.tags_json, '[]') AS tags_json,
                    COALESCE(a.note, '') AS note
                FROM customers c
                LEFT JOIN customer_annotations a ON a.customer_id = c.id
                WHERE {' AND '.join(clauses)}
                ORDER BY c.synced_at DESC
                """,
                params,
            ).fetchall()
            return [self._customer_summary(connection, row) for row in rows]

    def customer_detail(self, customer_id: str) -> dict:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT c.*, COALESCE(a.tags_json, '[]') AS tags_json,
                    COALESCE(a.note, '') AS note
                FROM customers c
                LEFT JOIN customer_annotations a ON a.customer_id = c.id
                WHERE c.id = ?
                """,
                (customer_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="客户不存在")
            payload = self._customer_summary(connection, row)
            payload["orders"] = [
                dict(order)
                for order in connection.execute(
                    """
                    SELECT id, order_no, status, amount_cents, created_at
                    FROM orders WHERE customer_id = ? ORDER BY created_at DESC
                    """,
                    (customer_id,),
                ).fetchall()
            ]
            payload["conversations"] = [
                dict(conversation)
                for conversation in connection.execute(
                    """
                    SELECT id, external_id, subject, state, last_message, updated_at
                    FROM conversations WHERE customer_id = ? ORDER BY updated_at DESC
                    """,
                    (customer_id,),
                ).fetchall()
            ]
        return payload

    def _customer_summary(self, connection, row) -> dict:
        metrics = connection.execute(
            """
            SELECT COUNT(*) AS order_count,
                COALESCE(SUM(CASE WHEN status IN ('待发货','已发货','已完成')
                    THEN amount_cents ELSE 0 END), 0) AS total_spent_cents
            FROM orders WHERE customer_id = ?
            """,
            (row["id"],),
        ).fetchone()
        payload = dict(row)
        payload["tags"] = json.loads(payload.pop("tags_json") or "[]")
        payload["phone_masked"] = mask_phone(payload["phone"])
        payload.update(dict(metrics))
        return payload

    def list_conversations(self, state: str = "") -> list[dict]:
        params: list[str] = []
        where = ""
        if state:
            where = "WHERE cv.state = ?"
            params.append(state)
        with connect(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT cv.*, c.name AS customer_name, c.phone AS customer_phone,
                    o.order_no,
                    (SELECT COUNT(*) FROM suggestions s
                        WHERE s.conversation_id = cv.id) AS suggestion_count
                FROM conversations cv
                JOIN customers c ON c.id = cv.customer_id
                LEFT JOIN orders o ON o.id = cv.order_id
                {where}
                ORDER BY cv.updated_at DESC
                """,
                params,
            ).fetchall()
        payload = []
        for row in rows:
            item = dict(row)
            item["customer_phone_masked"] = mask_phone(item["customer_phone"])
            payload.append(item)
        return payload

    def conversation_detail(self, conversation_id: str) -> dict:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT cv.*, c.name AS customer_name, c.phone AS customer_phone,
                    o.order_no, o.status AS order_status, o.logistics_status
                FROM conversations cv
                JOIN customers c ON c.id = cv.customer_id
                LEFT JOIN orders o ON o.id = cv.order_id
                WHERE cv.id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="会话不存在")
            messages = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY sent_at",
                (conversation_id,),
            ).fetchall()
            suggestions = connection.execute(
                "SELECT * FROM suggestions WHERE conversation_id = ? ORDER BY created_at DESC",
                (conversation_id,),
            ).fetchall()
            payload = dict(row)
            payload["customer_phone_masked"] = mask_phone(payload["customer_phone"])
            payload["messages"] = [dict(message) for message in messages]
            payload["suggestions"] = [
                self._suggestion_payload(connection, suggestion)
                for suggestion in suggestions
            ]
        return payload

    def _suggestion_payload(self, connection, row) -> dict:
        payload = dict(row)
        payload["suggestions"] = json.loads(payload.pop("suggestions_json"))
        payload["warnings"] = json.loads(payload.pop("warnings_json"))
        payload["sources"] = [
            dict(source)
            for source in connection.execute(
                "SELECT * FROM suggestion_sources WHERE suggestion_id = ? ORDER BY rank",
                (row["id"],),
            ).fetchall()
        ]
        return payload

    def dashboard(self) -> dict:
        with connect(self.db_path) as connection:
            counts = {
                "products": connection.execute("SELECT COUNT(*) FROM products").fetchone()[0],
                "skus": connection.execute("SELECT COUNT(*) FROM product_skus").fetchone()[0],
                "orders": connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
                "active_conversations": connection.execute(
                    "SELECT COUNT(*) FROM conversations WHERE state != '已关闭'"
                ).fetchone()[0],
                "messages_today": connection.execute(
                    "SELECT COUNT(*) FROM messages WHERE date(sent_at) = date('now')"
                ).fetchone()[0],
                "suggestions": connection.execute(
                    "SELECT COUNT(*) FROM suggestions"
                ).fetchone()[0],
            }
            setting_rows = connection.execute(
                "SELECT key, value FROM app_settings"
            ).fetchall()
            settings = {row["key"]: row["value"] for row in setting_rows}
            recent = connection.execute(
                """
                SELECT cv.id, cv.subject, cv.state, cv.last_message,
                    cv.updated_at, c.name AS customer_name
                FROM conversations cv JOIN customers c ON c.id = cv.customer_id
                ORDER BY cv.updated_at DESC LIMIT 4
                """
            ).fetchall()
            connection_row = connection.execute(
                "SELECT * FROM shop_connections LIMIT 1"
            ).fetchone()
        return {
            **counts,
            "model_configured": bool(
                settings.get("model_base_url") and settings.get("model_api_key")
            ),
            "last_webhook_at": settings.get("last_webhook_at"),
            "connection": dict(connection_row) if connection_row else None,
            "recent_conversations": [dict(item) for item in recent],
        }

    def integration_status(self) -> dict:
        with connect(self.db_path) as connection:
            connection_row = connection.execute(
                "SELECT * FROM shop_connections LIMIT 1"
            ).fetchone()
            settings = {
                row["key"]: row["value"]
                for row in connection.execute(
                    "SELECT key, value FROM app_settings"
                )
            }
            recent_events = connection.execute(
                """
                SELECT event_id, event_type, status, signature_valid,
                    received_at, processed_at
                FROM webhook_events ORDER BY received_at DESC LIMIT 10
                """
            ).fetchall()
            runs = connection.execute(
                "SELECT * FROM sync_runs ORDER BY finished_at DESC LIMIT 10"
            ).fetchall()
        return {
            "source": "douyin",
            "shop_name": connection_row["shop_name"],
            "connection_status": connection_row["connection_status"],
            "last_product_sync_at": connection_row["last_product_sync_at"],
            "last_order_sync_at": connection_row["last_order_sync_at"],
            "last_webhook_at": settings.get("last_webhook_at"),
            "webhook_path": "/integrations/doudian/feige/events",
            "recent_events": [dict(item) for item in recent_events],
            "sync_runs": [dict(item) for item in runs],
            "readonly": True,
        }
