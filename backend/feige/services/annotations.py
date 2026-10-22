from __future__ import annotations

import json
from pathlib import Path

from backend.feige.database import connect, utc_now


class AnnotationService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def update(
        self,
        customer_id: str,
        tags: list[str],
        note: str,
        actor: str,
    ) -> dict:
        now = utc_now()
        with connect(self.db_path) as connection:
            customer = connection.execute(
                "SELECT id FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()
            if not customer:
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="客户不存在")
            connection.execute(
                """
                INSERT INTO customer_annotations (
                    customer_id, tags_json, note, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    tags_json = excluded.tags_json,
                    note = excluded.note,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at
                """,
                (
                    customer_id,
                    json.dumps(tags, ensure_ascii=False),
                    note,
                    actor,
                    now,
                ),
            )
        return {
            "customer_id": customer_id,
            "tags": tags,
            "note": note,
            "updated_by": actor,
            "updated_at": now,
            "synced_to_douyin": False,
        }
