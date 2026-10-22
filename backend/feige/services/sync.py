from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from backend.feige.database import connect, utc_now
from backend.feige.domain import (
    OrderPayload,
    ProductPayload,
    SyncRunResult,
    WebhookResult,
)


class SyncService:
    def __init__(
        self,
        db_path: Path,
        adapter,
        webhook_secret: str,
        suggestion_service=None,
    ) -> None:
        self.db_path = db_path
        self.adapter = adapter
        self.webhook_secret = webhook_secret
        self.suggestion_service = suggestion_service

    def ingest_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
    ) -> WebhookResult:
        event_id = headers.get("X-Event-ID", "")
        if not event_id:
            try:
                event_id = json.loads(raw_body)["event_id"]
            except (json.JSONDecodeError, KeyError, TypeError):
                return WebhookResult(
                    status="processing_error",
                    event_id="",
                    detail="缺少事件 ID",
                )

        valid_signature = self.adapter.verify_webhook(raw_body, headers)
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            payload = {}

        now = utc_now()
        try:
            with connect(self.db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO webhook_events (
                        id, event_id, event_type, payload_json, signature_valid,
                        status, error, received_at, processed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?)
                    """,
                    (
                        str(uuid4()),
                        event_id,
                        payload.get("event_type", "unknown"),
                        json.dumps(payload, ensure_ascii=False),
                        int(valid_signature),
                        "validating" if valid_signature else "invalid_signature",
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError:
            return WebhookResult(status="duplicate", event_id=event_id)

        if not valid_signature:
            return WebhookResult(status="invalid_signature", event_id=event_id)

        message_id = None
        message_inserted = False
        try:
            with connect(self.db_path) as connection:
                event_type = payload.get("event_type")
                if event_type in {"buyer_message", "service_agent_message"}:
                    role = (
                        "buyer"
                        if event_type == "buyer_message"
                        else "service_agent"
                    )
                    conversation_id, message_id, message_inserted = self._upsert_message(
                        connection,
                        payload,
                        role,
                    )
                elif event_type == "product_changed":
                    self._upsert_product(connection, ProductPayload.model_validate(payload["product"]))
                elif event_type == "order_changed":
                    self._upsert_order(connection, OrderPayload.model_validate(payload["order"]))
                connection.execute(
                    """
                    UPDATE webhook_events SET status = 'processed', processed_at = ?
                    WHERE event_id = ?
                    """,
                    (utc_now(), event_id),
                )
                connection.execute(
                    """
                    INSERT INTO app_settings(key, value) VALUES ('last_webhook_at', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (utc_now(),),
                )
        except Exception as exc:
            with connect(self.db_path) as connection:
                connection.execute(
                    """
                    UPDATE webhook_events SET status = 'processing_error', error = ?
                    WHERE event_id = ?
                    """,
                    (str(exc)[:500], event_id),
                )
            return WebhookResult(
                status="processing_error",
                event_id=event_id,
                detail=str(exc)[:200],
            )

        if (
            payload.get("event_type") == "buyer_message"
            and message_inserted
            and message_id
            and self.suggestion_service is not None
        ):
            try:
                self.suggestion_service.generate(conversation_id, trigger="automatic")
            except Exception:
                self._record_event("suggestion_failed", {"event_id": event_id})

        return WebhookResult(
            status="accepted",
            event_id=event_id,
            message_id=message_id,
        )

    def _upsert_message(
        self,
        connection: sqlite3.Connection,
        payload: dict,
        role: str,
    ) -> tuple[str, str, bool]:
        external_conversation_id = payload["external_conversation_id"]
        conversation = connection.execute(
            "SELECT id, completeness FROM conversations WHERE external_id = ?",
            (external_conversation_id,),
        ).fetchone()
        if not conversation:
            customer = connection.execute(
                "SELECT id FROM customers ORDER BY created_at LIMIT 1"
            ).fetchone()
            conversation_id = str(uuid4())
            now = utc_now()
            connection.execute(
                """
                INSERT INTO conversations VALUES (?, ?, ?, NULL, '接待中',
                    'buyer_only', '飞鸽模拟会话', ?, ?, ?)
                """,
                (
                    conversation_id,
                    external_conversation_id,
                    customer["id"],
                    payload.get("text", ""),
                    now,
                    now,
                ),
            )
        else:
            conversation_id = conversation["id"]

        message_id = str(uuid4())
        external_message_id = payload["external_message_id"]
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO messages VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                message_id,
                external_message_id,
                conversation_id,
                role,
                payload.get("message_type", "text"),
                payload.get("text", ""),
                payload.get("sent_at", utc_now()),
                utc_now(),
            ),
        )
        inserted = cursor.rowcount == 1
        if not inserted:
            existing = connection.execute(
                "SELECT id FROM messages WHERE external_id = ?",
                (external_message_id,),
            ).fetchone()
            message_id = existing["id"]
        now = utc_now()
        completeness = (
            "complete"
            if role == "service_agent"
            else conversation["completeness"]
            if conversation
            else "buyer_only"
        )
        connection.execute(
            """
            UPDATE conversations SET last_message = ?, updated_at = ?,
                synced_at = ?, completeness = ?
            WHERE id = ?
            """,
            (payload.get("text", ""), now, now, completeness, conversation_id),
        )
        return conversation_id, message_id, inserted

    def pull_products(self) -> SyncRunResult:
        started = utc_now()
        success = 0
        failed = 0
        with connect(self.db_path) as connection:
            for product in self.adapter.pull_products():
                try:
                    self._upsert_product(connection, product)
                    success += 1
                except Exception:
                    failed += 1
            finished = utc_now()
            connection.execute(
                "INSERT INTO sync_runs VALUES (?, 'products', ?, ?, ?, ?, '')",
                (str(uuid4()), started, finished, success, failed),
            )
            connection.execute(
                """
                UPDATE shop_connections SET last_product_sync_at = ?
                """,
                (finished,),
            )
            product_count = connection.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0]
        return SyncRunResult(
            sync_type="products",
            success_count=success,
            failed_count=failed,
            product_count=product_count,
        )

    def pull_orders(self) -> SyncRunResult:
        started = utc_now()
        success = 0
        failed = 0
        with connect(self.db_path) as connection:
            for order in self.adapter.pull_orders():
                try:
                    self._upsert_order(connection, order)
                    success += 1
                except Exception:
                    failed += 1
            finished = utc_now()
            connection.execute(
                "INSERT INTO sync_runs VALUES (?, 'orders', ?, ?, ?, ?, '')",
                (str(uuid4()), started, finished, success, failed),
            )
            connection.execute(
                "UPDATE shop_connections SET last_order_sync_at = ?",
                (finished,),
            )
            order_count = connection.execute(
                "SELECT COUNT(*) FROM orders"
            ).fetchone()[0]
        return SyncRunResult(
            sync_type="orders",
            success_count=success,
            failed_count=failed,
            order_count=order_count,
        )

    def _upsert_product(
        self,
        connection: sqlite3.Connection,
        product: ProductPayload,
    ) -> None:
        now = utc_now()
        existing = connection.execute(
            "SELECT id FROM products WHERE external_id = ?",
            (product.external_id,),
        ).fetchone()
        product_id = existing["id"] if existing else str(uuid4())
        if existing:
            connection.execute(
                """
                UPDATE products SET title = ?, category = ?, image_emoji = ?,
                    status = ?, fabric = ?, source = 'douyin', synced_at = ?
                WHERE id = ?
                """,
                (
                    product.title,
                    product.category,
                    product.image_emoji,
                    product.status,
                    product.fabric,
                    now,
                    product_id,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, 'douyin', ?, ?)
                """,
                (
                    product_id,
                    product.external_id,
                    product.title,
                    product.category,
                    product.image_emoji,
                    product.status,
                    product.fabric,
                    now,
                    now,
                ),
            )
        for sku in product.skus:
            existing_sku = connection.execute(
                "SELECT id FROM product_skus WHERE external_id = ?",
                (sku["external_id"],),
            ).fetchone()
            if existing_sku:
                connection.execute(
                    """
                    UPDATE product_skus SET product_id = ?, sku_name = ?, color = ?,
                        size = ?, price_cents = ?, stock = ?, synced_at = ?
                    WHERE id = ?
                    """,
                    (
                        product_id,
                        sku["sku_name"],
                        sku.get("color", ""),
                        sku.get("size", ""),
                        sku["price_cents"],
                        sku["stock"],
                        now,
                        existing_sku["id"],
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO product_skus VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        sku["external_id"],
                        product_id,
                        sku["sku_name"],
                        sku.get("color", ""),
                        sku.get("size", ""),
                        sku["price_cents"],
                        sku["stock"],
                        now,
                    ),
                )

    def _upsert_order(
        self,
        connection: sqlite3.Connection,
        order: OrderPayload,
    ) -> None:
        customer = connection.execute(
            "SELECT id FROM customers WHERE external_id = ?",
            (order.customer_external_id,),
        ).fetchone()
        if not customer:
            raise ValueError("订单客户不存在")
        now = utc_now()
        existing = connection.execute(
            "SELECT id FROM orders WHERE external_id = ?",
            (order.external_id,),
        ).fetchone()
        order_id = existing["id"] if existing else str(uuid4())
        if existing:
            connection.execute(
                """
                UPDATE orders SET order_no = ?, customer_id = ?, amount_cents = ?,
                    status = ?, logistics_status = ?, after_sales_status = ?,
                    source = 'douyin', synced_at = ?
                WHERE id = ?
                """,
                (
                    order.order_no,
                    customer["id"],
                    order.amount_cents,
                    order.status,
                    order.logistics_status,
                    order.after_sales_status,
                    now,
                    order_id,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'douyin', ?, ?)
                """,
                (
                    order_id,
                    order.external_id,
                    order.order_no,
                    customer["id"],
                    order.amount_cents,
                    order.status,
                    order.logistics_status,
                    order.after_sales_status,
                    order.created_at.isoformat(),
                    now,
                ),
            )
        for item in order.items:
            product = connection.execute(
                "SELECT id FROM products WHERE external_id = ?",
                (item["product_external_id"],),
            ).fetchone()
            sku = connection.execute(
                "SELECT id, sku_name FROM product_skus WHERE external_id = ?",
                (item["sku_external_id"],),
            ).fetchone()
            if not product or not sku:
                raise ValueError("订单商品或 SKU 不存在")
            existing_item = connection.execute(
                "SELECT id FROM order_items WHERE external_id = ?",
                (item["external_id"],),
            ).fetchone()
            if existing_item:
                connection.execute(
                    """
                    UPDATE order_items SET order_id = ?, product_id = ?, sku_id = ?,
                        product_name = ?, sku_name = ?, unit_price_cents = ?, quantity = ?
                    WHERE id = ?
                    """,
                    (
                        order_id,
                        product["id"],
                        sku["id"],
                        item["product_name"],
                        item.get("sku_name", sku["sku_name"]),
                        item["unit_price_cents"],
                        item["quantity"],
                        existing_item["id"],
                    ),
                )
            else:
                connection.execute(
                    "INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        item["external_id"],
                        order_id,
                        product["id"],
                        sku["id"],
                        item["product_name"],
                        item.get("sku_name", sku["sku_name"]),
                        item["unit_price_cents"],
                        item["quantity"],
                    ),
                )

    def _record_event(self, event_type: str, payload: dict) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO analytics_events VALUES (?, ?, ?, ?)",
                (
                    str(uuid4()),
                    event_type,
                    json.dumps(payload, ensure_ascii=False),
                    utc_now(),
                ),
            )
