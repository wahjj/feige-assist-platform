from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from backend.feige.database import connect
from backend.feige.domain import OrderPayload, ProductPayload, ShopConnection


class MockDouyinAdapter:
    def __init__(self, db_path: Path, webhook_secret: str) -> None:
        self.db_path = db_path
        self.webhook_secret = webhook_secret

    def exchange_demo_oauth(self) -> ShopConnection:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM shop_connections ORDER BY authorized_at DESC LIMIT 1"
            ).fetchone()
        return ShopConnection(
            id=row["id"],
            shop_external_id=row["shop_external_id"],
            shop_name=row["shop_name"],
            connection_status=row["connection_status"],
            last_product_sync_at=row["last_product_sync_at"],
            last_order_sync_at=row["last_order_sync_at"],
        )

    def pull_products(self) -> list[ProductPayload]:
        with connect(self.db_path) as connection:
            products = connection.execute(
                "SELECT * FROM products ORDER BY created_at"
            ).fetchall()
            payloads = []
            for product in products:
                skus = connection.execute(
                    "SELECT * FROM product_skus WHERE product_id = ? ORDER BY size",
                    (product["id"],),
                ).fetchall()
                payloads.append(
                    ProductPayload(
                        external_id=product["external_id"],
                        title=product["title"],
                        category=product["category"],
                        image_emoji=product["image_emoji"],
                        status=product["status"],
                        fabric=product["fabric"],
                        skus=[
                            {
                                "external_id": sku["external_id"],
                                "sku_name": sku["sku_name"],
                                "color": sku["color"],
                                "size": sku["size"],
                                "price_cents": sku["price_cents"],
                                "stock": sku["stock"],
                            }
                            for sku in skus
                        ],
                    )
                )
        return payloads

    def pull_orders(self) -> list[OrderPayload]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT o.*, c.external_id AS customer_external_id
                FROM orders o JOIN customers c ON c.id = o.customer_id
                ORDER BY o.created_at
                """
            ).fetchall()
            payloads = []
            for order in rows:
                items = connection.execute(
                    """
                    SELECT oi.*, p.external_id AS product_external_id,
                           s.external_id AS sku_external_id
                    FROM order_items oi
                    JOIN products p ON p.id = oi.product_id
                    JOIN product_skus s ON s.id = oi.sku_id
                    WHERE oi.order_id = ?
                    """,
                    (order["id"],),
                ).fetchall()
                payloads.append(
                    OrderPayload(
                        external_id=order["external_id"],
                        order_no=order["order_no"],
                        customer_external_id=order["customer_external_id"],
                        amount_cents=order["amount_cents"],
                        status=order["status"],
                        logistics_status=order["logistics_status"],
                        after_sales_status=order["after_sales_status"],
                        created_at=order["created_at"],
                        items=[
                            {
                                "external_id": item["external_id"],
                                "product_external_id": item["product_external_id"],
                                "sku_external_id": item["sku_external_id"],
                                "product_name": item["product_name"],
                                "sku_name": item["sku_name"],
                                "unit_price_cents": item["unit_price_cents"],
                                "quantity": item["quantity"],
                            }
                            for item in items
                        ],
                    )
                )
        return payloads

    def verify_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
    ) -> bool:
        supplied = headers.get("X-Signature", "")
        expected = hmac.new(
            self.webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return bool(supplied) and hmac.compare_digest(supplied, expected)
