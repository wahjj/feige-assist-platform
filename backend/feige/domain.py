from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SkuView(BaseModel):
    id: UUID
    external_id: str
    sku_name: str
    color: str
    size: str
    price_cents: int
    stock: int
    synced_at: datetime


class ProductView(BaseModel):
    id: UUID
    external_id: str
    title: str
    category: str
    image_emoji: str
    status: str
    fabric: str
    source: str = "douyin"
    synced_at: datetime
    knowledge_bound: bool = False
    skus: list[SkuView] = Field(default_factory=list)


class OrderItemView(BaseModel):
    id: UUID
    product_id: UUID
    sku_id: UUID
    product_name: str
    sku_name: str
    unit_price_cents: int
    quantity: int


class OrderView(BaseModel):
    id: UUID
    external_id: str
    order_no: str
    customer_id: UUID
    customer_name: str
    amount_cents: int
    status: str
    logistics_status: str
    after_sales_status: str
    created_at: datetime
    synced_at: datetime
    source: str = "douyin"
    items: list[OrderItemView] = Field(default_factory=list)


class CustomerView(BaseModel):
    id: UUID
    external_id: str
    name: str
    phone: str
    phone_masked: str
    tags: list[str] = Field(default_factory=list)
    note: str = ""
    order_count: int = 0
    total_spent_cents: int = 0
    synced_at: datetime
    source: str = "douyin"


class MessageView(BaseModel):
    id: UUID
    external_id: str
    role: Literal["buyer", "service_agent", "unknown"]
    message_type: str
    content: str
    sent_at: datetime
    synced_at: datetime


class SuggestionItem(BaseModel):
    style: str
    text: str


class SuggestionSourceView(BaseModel):
    knowledge_id: UUID | None = None
    title: str
    product_id: UUID | None = None
    sku_id: UUID | None = None
    rank: int


class SuggestionView(BaseModel):
    id: UUID
    conversation_id: UUID
    status: str
    trigger: str
    suggestions: list[SuggestionItem] = Field(default_factory=list)
    sources: list[SuggestionSourceView] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_name: str = ""
    created_at: datetime
    copied_count: int = 0


class ConversationView(BaseModel):
    id: UUID
    external_id: str
    customer_id: UUID
    customer_name: str
    customer_phone_masked: str
    order_id: UUID | None = None
    state: str
    completeness: str
    subject: str
    last_message: str
    updated_at: datetime
    synced_at: datetime
    messages: list[MessageView] = Field(default_factory=list)
    suggestions: list[SuggestionView] = Field(default_factory=list)


class KnowledgeHit(BaseModel):
    entry_id: UUID
    title: str
    snippet: str
    score: int
    product_id: UUID | None = None
    category: str | None = None


class WebhookResult(BaseModel):
    status: Literal["accepted", "duplicate", "invalid_signature", "processing_error"]
    event_id: str
    message_id: UUID | None = None
    detail: str = ""


class SyncRunResult(BaseModel):
    sync_type: str
    success_count: int
    failed_count: int
    product_count: int = 0
    order_count: int = 0


class ProductPayload(BaseModel):
    external_id: str
    title: str
    category: str
    image_emoji: str = "👗"
    status: str = "在售"
    fabric: str = ""
    skus: list[dict[str, Any]]


class OrderPayload(BaseModel):
    external_id: str
    order_no: str
    customer_external_id: str
    amount_cents: int
    status: str
    logistics_status: str = "暂无物流"
    after_sales_status: str = "无"
    created_at: datetime
    items: list[dict[str, Any]]


class ShopConnection(BaseModel):
    id: UUID
    shop_external_id: str
    shop_name: str
    connection_status: str
    last_product_sync_at: datetime | None = None
    last_order_sync_at: datetime | None = None
