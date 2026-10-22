from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from backend.feige.database import connect, utc_now
from backend.feige.domain import KnowledgeHit


def normalize_terms(text: str) -> list[str]:
    return [
        term.lower()
        for term in re.split(r"[\s,，。！？、;；:：/]+", text)
        if term.strip()
    ]


class KnowledgeService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def list_entries(
        self,
        query: str = "",
        entry_type: str = "",
    ) -> list[dict]:
        clauses = ["1 = 1"]
        params: list[str] = []
        if query:
            like = f"%{query}%"
            clauses.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ?)")
            params.extend([like, like, like])
        if entry_type:
            clauses.append("entry_type = ?")
            params.append(entry_type)
        with connect(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM knowledge_entries
                WHERE {' AND '.join(clauses)}
                ORDER BY enabled DESC, updated_at DESC
                """,
                params,
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def create(self, payload: dict) -> dict:
        entry_id = str(uuid4())
        now = utc_now()
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO knowledge_entries VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?
                )
                """,
                (
                    entry_id,
                    payload["entry_type"],
                    payload["title"],
                    payload["content"],
                    payload.get("keywords", ""),
                    payload.get("product_id"),
                    payload.get("category"),
                    int(payload.get("enabled", True)),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM knowledge_entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return self._serialize(row)

    def update(self, entry_id: str, payload: dict) -> dict:
        allowed = {
            "entry_type",
            "title",
            "content",
            "keywords",
            "product_id",
            "category",
            "enabled",
        }
        fields = {key: value for key, value in payload.items() if key in allowed}
        if "enabled" in fields:
            fields["enabled"] = int(bool(fields["enabled"]))
        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with connect(self.db_path) as connection:
            cursor = connection.execute(
                f"UPDATE knowledge_entries SET {assignments} WHERE id = ?",
                [*fields.values(), entry_id],
            )
            if cursor.rowcount == 0:
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="知识条目不存在")
            row = connection.execute(
                "SELECT * FROM knowledge_entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return self._serialize(row)

    def delete(self, entry_id: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "DELETE FROM knowledge_entries WHERE id = ?", (entry_id,)
            )

    def retrieve(
        self,
        query: str,
        product_id: str | None = None,
        category: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeHit]:
        terms = normalize_terms(query)
        lowered_query = query.lower()
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_entries WHERE enabled = 1"
            ).fetchall()

        scored: list[KnowledgeHit] = []
        for row in rows:
            score = 0
            if product_id and row["product_id"] == product_id:
                score += 100
            if category and row["category"] == category:
                score += 45
            keyword_list = normalize_terms(row["keywords"].replace(",", "，"))
            for term in terms:
                if term and any(term in keyword or keyword in term for keyword in keyword_list):
                    score += 20
                if term and term in row["title"].lower():
                    score += 15
                if term and term in row["content"].lower():
                    score += 8
            if row["title"].lower() in lowered_query:
                score += 15
            if score <= 0:
                continue
            scored.append(
                KnowledgeHit(
                    entry_id=row["id"],
                    title=row["title"],
                    snippet=row["content"][:180],
                    score=score,
                    product_id=row["product_id"],
                    category=row["category"],
                )
            )
        scored.sort(key=lambda item: (-item.score, item.title))
        return scored[:limit]

    def _serialize(self, row) -> dict:
        payload = dict(row)
        payload["enabled"] = bool(payload["enabled"])
        return payload
