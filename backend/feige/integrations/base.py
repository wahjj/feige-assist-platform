from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from backend.feige.domain import OrderPayload, ProductPayload, ShopConnection


class DouyinReadAdapter(Protocol):
    def exchange_demo_oauth(self) -> ShopConnection: ...

    def pull_products(self) -> list[ProductPayload]: ...

    def pull_orders(self) -> list[OrderPayload]: ...

    def verify_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
    ) -> bool: ...
