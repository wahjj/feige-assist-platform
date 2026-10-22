# 飞鸽只读 AI 辅助中台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有可写商家后台重构为本地可运行的飞鸽只读辅助中台，提供模拟同步、商品/SKU、订单、客户档案、本地 RAG 建议、业务分析及真实模型配置。

**Architecture:** 保留 Vue 3 + FastAPI + SQLite 技术栈，在 `backend/feige` 下建立独立的只读镜像、同步适配器、知识检索、AI 建议和分析模块。前端继续使用现有视觉系统，但移除所有发送、接管和外写功能，改为只读会话中心、AI 建议和同步观测页面。

**Tech Stack:** Python 3.11+、FastAPI、SQLite、Vue 3、Vue Router、Vite、JavaScript、Vitest、pytest。

**Spec:** `docs/superpowers/specs/2026-10-22-feige-assist-middle-platform-design.md`

## Global Constraints

- 飞鸽是唯一客服接待入口，中台不能发送任何买家消息。
- 中台不能接管会话、分配客服、分流、计时或计算客服绩效。
- 商品、SKU、价格、库存、订单、物流和售后状态只能从抖店单向同步并在中台只读展示。
- 平台业务以抖店为准，同步数据必须显示来源和最后同步时间。
- 客户基础资料只读；仅中台标签和跟进备注可编辑，且不得回写抖店。
- 商品模型必须为“商品 + 多个 SKU”，SKU 包含尺码、规格、价格和库存。
- 会话模型必须支持买家消息、客服消息、图片消息和未知角色。
- AI 仅生成参考建议，不写入真实会话消息，不自动发送。
- 未配置真实 OpenAI 兼容模型时，不得生成模拟 AI 建议。
- 本地 RAG 使用关键词/全文召回，最多 5 条知识来源，不接向量数据库。
- 新买家消息保存后，模型已配置时自动生成一次建议；页面保留“重新生成”。
- 建议包含专业说明、简洁直接、温和安抚三条，敏感词命中时禁止复制。
- Webhook 必须验签、去重，并通过模拟事件入口进入同一同步流程。
- 当前阶段不接真实抖店授权；适配器接口和模拟实现必须可替换。
- 前端使用 Vue 3、Vite 和 JavaScript；不使用 TypeScript 或 Java。
- 服务只监听 `127.0.0.1`，当前阶段不做公网部署。
- `/panel` 只显示飞鸽侧栏预留说明，不实现任何侧栏功能。
- 业务分析只展示中台独有数据，不复制飞鸽客服绩效。
- 保留用户现有 `docs/mockups/` 内容，不改写或删除。
- 保留用户当前修改过的 `start.bat` 功能，只做必要的启动地址和说明调整。

---

## File Structure

| Path | Responsibility |
|---|---|
| `backend/main.py` | 仅保留应用导出和兼容入口，最终切换到新应用工厂 |
| `backend/feige/app.py` | FastAPI 应用工厂与路由装配 |
| `backend/feige/auth.py` | 管理员会话、API Key 和 CSRF |
| `backend/feige/database.py` | SQLite v2 Schema、连接和模拟种子 |
| `backend/feige/domain.py` | 只读 DTO、事件和 AI 建议 Pydantic 模型 |
| `backend/feige/integrations/base.py` | 抖店读取适配器 Protocol |
| `backend/feige/integrations/mock_douyin.py` | 本地模拟 OAuth、商品和订单拉取 |
| `backend/feige/services/sync.py` | Webhook 验签、去重、映射和同步 |
| `backend/feige/services/read_queries.py` | 商品、SKU、订单、客户、会话只读查询 |
| `backend/feige/services/annotations.py` | 客户本地标签和备注 |
| `backend/feige/services/knowledge.py` | 知识条目 CRUD 与本地检索 |
| `backend/feige/services/assistant.py` | 上下文组装、模型调用、建议校验和敏感词检查 |
| `backend/feige/services/analytics.py` | 咨询分类、建议与同步指标 |
| `backend/feige/api/admin.py` | 管理员只读、知识、建议和分析 API |
| `backend/feige/api/integration.py` | OAuth 占位、Webhook、拉取和模拟事件 API |
| `frontend/src/router.js` | 新中台路由与 `/panel` 占位 |
| `frontend/src/components/AppShell.vue` | 新导航与只读提示 |
| `frontend/src/views/OverviewView.vue` | 中台概览 |
| `frontend/src/views/ConversationsView.vue` | 只读会话中心和 AI 建议 |
| `frontend/src/views/ProductsView.vue` | 只读商品及 SKU |
| `frontend/src/views/OrdersView.vue` | 只读订单查询 |
| `frontend/src/views/CustomersView.vue` | 客户镜像与本地标注 |
| `frontend/src/views/KnowledgeView.vue` | RAG 知识库维护 |
| `frontend/src/views/AnalyticsView.vue` | 中台独有业务分析 |
| `frontend/src/views/SyncSettingsView.vue` | 授权、Webhook、拉取、模型和日志 |
| `frontend/src/views/MockEventsView.vue` | 模拟飞鸽事件 |
| `frontend/src/views/PanelPlaceholderView.vue` | 飞鸽侧栏预留 |
| `tests/feige/` | 同步、只读、RAG、建议和分析测试 |
| `frontend/src/**/*.spec.js` | 新页面和只读交互测试 |

---

### Task 1: 只读数据模型与商品/SKU 种子

**Files:**
- Create: `backend/feige/__init__.py`
- Create: `backend/feige/domain.py`
- Create: `backend/feige/database.py`
- Create: `tests/feige/__init__.py`
- Create: `tests/feige/test_database.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Python 标准库 `sqlite3`。
- Produces: `connect(db_path: Path) -> sqlite3.Connection`；`init_database(db_path: Path) -> None`；`seed_demo(connection, force: bool = False) -> None`；领域 DTO `ProductView`、`SkuView`、`OrderView`、`OrderItemView`、`CustomerView`、`ConversationView`、`MessageView`、`SyncStatusView`。

- [ ] **Step 1: 写数据库失败测试**

```python
from pathlib import Path

from backend.feige.database import connect, init_database


def test_seed_contains_product_with_multiple_skus(tmp_path: Path) -> None:
    db_path = tmp_path / "feige.db"
    init_database(db_path)

    with connect(db_path) as connection:
        product = connection.execute(
            "SELECT id, title, source FROM products LIMIT 1"
        ).fetchone()
        skus = connection.execute(
            "SELECT sku_name, size, price_cents, stock FROM product_skus WHERE product_id = ?",
            (product["id"],),
        ).fetchall()

    assert product["source"] == "douyin"
    assert product["title"]
    assert len(skus) >= 2
    assert skus[0]["size"]
    assert skus[0]["price_cents"] > 0
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_database.py -v`

Expected: FAIL，因为 `backend.feige` 和 v2 数据库尚不存在。

- [ ] **Step 3: 创建 SQLite v2 Schema**

新数据库文件使用 `data/feige_assist.db`，不改写旧 `data/demo.db`。

表至少包含：

- `admin_accounts`
- `shop_connections`
- `products`
- `product_skus`
- `orders`
- `order_items`
- `customers`
- `customer_annotations`
- `conversations`
- `messages`
- `knowledge_entries`
- `suggestions`
- `suggestion_sources`
- `webhook_events`
- `sync_runs`
- `analytics_events`
- `app_settings`

关键约束：

- 外部 ID 唯一：商品、SKU、订单、客户、会话、消息。
- `messages.role` 限定为 `buyer`、`service_agent`、`unknown`。
- `products.source` 和 `orders.source` 固定为 `douyin`。
- 金额使用整数分。
- 时间使用 UTC ISO 字符串。
- `customer_annotations` 独立于客户镜像表。
- 不存在任何中台消息发送表或飞鸽外发记录表。

- [ ] **Step 4: 创建服装品类模拟数据**

种子至少包含：

- 6 个服装商品。
- 每个商品 2–4 个 SKU，覆盖尺码、颜色、价格和库存。
- 5 个客户。
- 6 个订单，订单商品明细引用 SKU。
- 4 个会话，其中至少 1 个“完整”、1 个“仅买家消息”。
- 主演示会话的外部 ID 固定为 `conv-demo-001`，供模拟 Webhook 和测试使用。
- 种子消息外部 ID 使用 `msg-demo-` 前缀，避免与测试事件 `msg-001` 冲突。
- 每个会话有 2–6 条买家/客服消息。
- 10 条服装知识：尺码、面料、养护、售后、搭配和 FAQ。
- 2 条历史 AI 建议及来源。
- 1 条模拟 OAuth 连接和 2 条同步记录。

`seed_demo` 只在数据库为空时执行，重复调用不重复插入。

- [ ] **Step 5: 运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_database.py -v`

Expected: PASS。

```bash
git add backend/feige tests/feige .gitignore
git commit -m "feat: add readonly Feige mirror schema"
```

---

### Task 2: 模拟抖店适配器、Webhook 与同步

**Files:**
- Create: `backend/feige/integrations/__init__.py`
- Create: `backend/feige/integrations/base.py`
- Create: `backend/feige/integrations/mock_douyin.py`
- Create: `backend/feige/services/__init__.py`
- Create: `backend/feige/services/sync.py`
- Create: `tests/feige/test_sync.py`

**Interfaces:**
- Consumes: v2 数据库和领域模型。
- Produces: `DouyinReadAdapter` Protocol；`MockDouyinAdapter(db_path, webhook_secret)`；`SyncService(db_path, adapter, webhook_secret, suggestion_service=None)`；`SyncService.ingest_webhook(raw_body: bytes, headers: Mapping[str, str]) -> WebhookResult`；`SyncService.pull_products() -> SyncRunResult`；`SyncService.pull_orders() -> SyncRunResult`。

- [ ] **Step 1: 写 Webhook 去重失败测试**

```python
from uuid import uuid4


def test_webhook_event_is_processed_only_once(sync_context) -> None:
    event = sync_context.buyer_message_event("event-001")

    first = sync_context.service.ingest_webhook(event.body, event.headers)
    second = sync_context.service.ingest_webhook(event.body, event.headers)

    assert first.status == "accepted"
    assert second.status == "duplicate"
    with sync_context.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM messages WHERE external_message_id = ?",
            ("msg-001",),
        ).fetchone()[0] == 1
```

- [ ] **Step 2: 写验签与只读拉取失败测试**

```python
def test_invalid_signature_is_rejected(sync_context) -> None:
    event = sync_context.buyer_message_event("event-002", valid_signature=False)

    result = sync_context.service.ingest_webhook(event.body, event.headers)

    assert result.status == "invalid_signature"


def test_pull_products_upserts_skus_without_writeback(sync_context) -> None:
    result = sync_context.service.pull_products()

    assert result.success_count >= 6
    assert result.failed_count == 0
    assert not hasattr(sync_context.adapter, "update_product")
```

- [ ] **Step 3: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_sync.py -v`

Expected: FAIL，因为适配器和同步服务不存在。

- [ ] **Step 4: 实现只读适配器与同步**

在 `tests/feige/conftest.py` 增加可直接运行的同步夹具：

```python
import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.feige.database import connect, init_database
from backend.feige.integrations.mock_douyin import MockDouyinAdapter
from backend.feige.services.sync import SyncService


@dataclass
class SignedEvent:
    body: bytes
    headers: dict[str, str]


def make_buyer_message_event(
    event_id: str,
    valid_signature: bool = True,
) -> SignedEvent:
    payload = {
        "event_id": event_id,
        "event_type": "buyer_message",
        "external_conversation_id": "conv-demo-001",
        "external_message_id": "msg-001",
        "text": "这条裙子我身高165，应该选什么码？",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    if not valid_signature:
        signature = "invalid"
    return SignedEvent(
        body=body,
        headers={"X-Event-ID": event_id, "X-Signature": signature},
    )


class SyncContext:
    def __init__(self, tmp_path: Path) -> None:
        self.db_path = tmp_path / "feige.db"
        init_database(self.db_path)
        self.adapter = MockDouyinAdapter(self.db_path, "webhook-secret")
        self.service = SyncService(self.db_path, self.adapter, "webhook-secret")

    def connect(self):
        return connect(self.db_path)

    def buyer_message_event(
        self,
        event_id: str,
        valid_signature: bool = True,
    ) -> SignedEvent:
        return make_buyer_message_event(event_id, valid_signature)


@pytest.fixture
def sync_context(tmp_path):
    return SyncContext(tmp_path)
```

`DouyinReadAdapter` 只暴露：

```python
class DouyinReadAdapter(Protocol):
    def exchange_demo_oauth(self) -> ShopConnection: ...
    def pull_products(self) -> list[ProductPayload]: ...
    def pull_orders(self) -> list[OrderPayload]: ...
    def verify_webhook(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...
```

不得出现 `send_message`、`update_order`、`update_product` 或 `takeover_conversation`。

同步服务要求：

- 使用 HMAC-SHA256 模拟验签。
- 通过 `X-Event-ID` 和数据库唯一约束去重。
- 事件载荷先生成 `webhook_events` 记录，再执行归一化。
- 买家消息、客服消息和未知角色正确映射。
- 商品、SKU、订单和订单明细按外部 ID 幂等 upsert。
- 同步失败记录 `sync_runs` 并保留旧数据。
- 模拟事件与“真实 Webhook”调用同一个 `ingest_webhook`。
- 新买家消息成功保存后发布 `buyer_message_received` 内部事件，供建议服务订阅。

- [ ] **Step 5: 运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_sync.py -v`

Expected: PASS。

```bash
git add backend/feige/integrations backend/feige/services/sync.py tests/feige/test_sync.py
git commit -m "feat: add simulated Douyin webhook and readonly sync"
```

---

### Task 3: 管理员认证与只读 API

**Files:**
- Create: `backend/feige/auth.py`
- Create: `backend/feige/services/read_queries.py`
- Create: `backend/feige/api/__init__.py`
- Create: `backend/feige/api/admin.py`
- Create: `backend/feige/api/integration.py`
- Create: `backend/feige/app.py`
- Create: `tests/feige/conftest.py`
- Create: `tests/feige/test_admin_api.py`

**Interfaces:**
- Consumes: v2 数据库和 `SyncService`。
- Produces: `create_feige_app(db_path: Path | None = None, session_secret: str = ...) -> FastAPI`；管理员会话和 CSRF；只读商品/订单/客户/会话 API；同步状态和手动拉取 API。

- [ ] **Step 1: 写只读 API 失败测试**

```python
def test_product_detail_contains_skus(admin_client) -> None:
    products = admin_client.get("/api/products").json()
    detail = admin_client.get(f"/api/products/{products[0]['id']}").json()

    assert products[0]["source"] == "douyin"
    assert len(detail["skus"]) >= 2
    assert detail["skus"][0]["size"]


def test_external_resources_have_no_write_routes(admin_client) -> None:
    product = admin_client.get("/api/products").json()[0]

    assert admin_client.post("/api/products", json={"title": "新商品"}).status_code == 405
    assert admin_client.put(f"/api/products/{product['id']}", json={}).status_code == 405
    assert admin_client.post(
        f"/api/conversations/{uuid4()}/messages",
        json={"text": "不应发送"},
    ).status_code in {404, 405}
```

- [ ] **Step 2: 写 Webhook 与模拟拉取 API 测试**

```python
def test_sync_status_reports_readonly_source(admin_client) -> None:
    payload = admin_client.get("/api/integration/status").json()

    assert payload["source"] == "douyin"
    assert payload["connection_status"] == "demo_connected"
    assert "last_product_sync_at" in payload


def test_manual_pull_products_is_idempotent(admin_client) -> None:
    first = admin_client.post("/api/integration/pull/products").json()
    second = admin_client.post("/api/integration/pull/products").json()

    assert first["success_count"] >= 6
    assert second["success_count"] >= 6
    assert first["product_count"] == second["product_count"]
```

- [ ] **Step 3: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_admin_api.py -v`

Expected: FAIL，因为新应用工厂、鉴权和只读 API 不存在。

- [ ] **Step 4: 实现认证与路由**

在 `tests/feige/conftest.py` 增加应用夹具：

```python
from fastapi.testclient import TestClient

from backend.feige.app import create_feige_app


@pytest.fixture
def app(tmp_path):
    return create_feige_app(
        db_path=tmp_path / "feige.db",
        session_secret="test-secret",
    )


@pytest.fixture
def admin_client(app):
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        client.headers.update({"X-CSRF-Token": client.cookies["csrf_token"]})
        yield client
```

沿用现有 PBKDF2 密码哈希、HMAC 会话 Cookie 和 CSRF Header 设计，但拆到 `auth.py`。

管理员 API：

- `GET /api/dashboard`
- `GET /api/products`
- `GET /api/products/{id}`
- `GET /api/orders`
- `GET /api/orders/{id}`
- `GET /api/customers`
- `GET /api/customers/{id}`
- `GET /api/conversations`
- `GET /api/conversations/{id}`
- `GET /api/integration/status`
- `POST /api/integration/pull/products`
- `POST /api/integration/pull/orders`

只读接口响应必须包含 `source`、`synced_at` 和明确关联数据。所有 POST 除登录、模拟 Webhook、拉取和 AI 建议外必须校验 CSRF。

刻意不注册：

- `POST /api/conversations/{id}/messages`
- `POST /api/conversations/{id}/takeover`
- `POST/PUT/DELETE /api/products/*`
- `PATCH /api/orders/*`
- `POST /api/approvals/*`

- [ ] **Step 5: 运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_admin_api.py -v`

Expected: PASS。

```bash
git add backend/feige/auth.py backend/feige/app.py backend/feige/api backend/feige/services/read_queries.py tests/feige
git commit -m "feat: expose readonly Feige admin API"
```

---

### Task 4: 客户本地标注与知识库检索

**Files:**
- Create: `backend/feige/services/annotations.py`
- Create: `backend/feige/services/knowledge.py`
- Modify: `backend/feige/api/admin.py`
- Create: `tests/feige/test_annotations.py`
- Create: `tests/feige/test_knowledge.py`

**Interfaces:**
- Consumes: v2 数据库。
- Produces: `AnnotationService.update(customer_id, tags, note, actor) -> AnnotationView`；`KnowledgeService.list/create/update/delete`；`KnowledgeService.retrieve(query, product_id, category, limit=5) -> list[KnowledgeHit]`。

- [ ] **Step 1: 写客户标注边界测试**

```python
def test_customer_annotation_does_not_change_mirror(admin_client) -> None:
    customer = admin_client.get("/api/customers").json()[0]
    original_name = customer["name"]

    response = admin_client.put(
        f"/api/customers/{customer['id']}/annotations",
        json={"tags": ["高复购", "尺码咨询"], "note": "偏好通勤风格"},
    )
    detail = admin_client.get(f"/api/customers/{customer['id']}").json()

    assert response.status_code == 200
    assert detail["name"] == original_name
    assert detail["tags"] == ["高复购", "尺码咨询"]
    assert detail["note"] == "偏好通勤风格"
```

- [ ] **Step 2: 写知识库检索失败测试**

```python
def test_product_bound_knowledge_ranks_before_general(knowledge_service, seeded_ids) -> None:
    hits = knowledge_service.retrieve(
        query="这条裙子偏大吗，身高 165 怎么选",
        product_id=seeded_ids["product_id"],
        category="连衣裙",
        limit=5,
    )

    assert len(hits) <= 5
    assert hits[0].product_id == seeded_ids["product_id"]
    assert "尺码" in hits[0].title
```

- [ ] **Step 3: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_annotations.py tests/feige/test_knowledge.py -v`

Expected: FAIL，因为标注和知识服务不存在。

- [ ] **Step 4: 实现标注与本地 RAG 检索**

在 `tests/feige/conftest.py` 增加知识库夹具：

```python
from backend.feige.database import connect
from backend.feige.services.knowledge import KnowledgeService


@pytest.fixture
def knowledge_service(tmp_path):
    from backend.feige.database import init_database

    db_path = tmp_path / "knowledge.db"
    init_database(db_path)
    return KnowledgeService(db_path)


@pytest.fixture
def seeded_ids(tmp_path):
    from backend.feige.database import init_database

    db_path = tmp_path / "knowledge.db"
    init_database(db_path)
    with connect(db_path) as connection:
        product = connection.execute(
            "SELECT id, category FROM products ORDER BY created_at LIMIT 1"
        ).fetchone()
    return {"product_id": product["id"], "category": product["category"]}
```

标注服务只更新 `customer_annotations`，禁止更新 `customers` 镜像字段。

检索权重固定为：

1. 精确商品绑定：+100。
2. 商品分类绑定：+45。
3. 关键词命中：每个 +20。
4. 标题命中：额外 +15。
5. 正文命中：每个 +8。

只检索启用知识，最多返回 5 条，返回 `entry_id`、`title`、`snippet`、`score`、`product_id` 和 `category`。

- [ ] **Step 5: 运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_annotations.py tests/feige/test_knowledge.py -v`

Expected: PASS。

```bash
git add backend/feige/services/annotations.py backend/feige/services/knowledge.py backend/feige/api/admin.py tests/feige
git commit -m "feat: add customer annotations and local RAG retrieval"
```

---

### Task 5: 真实模型网关与 AI 建议

**Files:**
- Create: `backend/feige/services/assistant.py`
- Modify: `backend/feige/api/admin.py`
- Modify: `backend/feige/services/sync.py`
- Create: `tests/feige/test_assistant.py`

**Interfaces:**
- Consumes: `KnowledgeService.retrieve`、只读查询、同步事件。
- Produces: `ModelGateway(client: httpx.Client, base_url: str, model: str, api_key: str).generate(messages: list[dict]) -> str`；`SuggestionService(db_path, knowledge_service, model_gateway).generate(conversation_id: UUID, trigger: str) -> SuggestionView`；`SuggestionService.list_for_conversation(conversation_id) -> list[SuggestionView]`；`SuggestionService.track_copy(suggestion_id: UUID) -> None`。

- [ ] **Step 1: 写模型未配置失败测试**

```python
def test_suggestion_fails_cleanly_when_model_is_not_configured(tmp_path) -> None:
    from backend.feige.database import connect, init_database
    from backend.feige.services.assistant import SuggestionService
    from backend.feige.services.knowledge import KnowledgeService

    db_path = tmp_path / "unconfigured.db"
    init_database(db_path)
    with connect(db_path) as connection:
        conversation_id = connection.execute(
            "SELECT id FROM conversations LIMIT 1"
        ).fetchone()["id"]
    suggestion_service = SuggestionService(
        db_path,
        KnowledgeService(db_path),
        model_gateway=None,
    )

    with pytest.raises(ModelNotConfigured):
        suggestion_service.generate(conversation_id, trigger="manual")

    assert suggestion_service.list_for_conversation(conversation_id) == []
```

- [ ] **Step 2: 写建议结构、来源和敏感词失败测试**

```python
def test_suggestion_contains_three_styles_and_sources(suggestion_context) -> None:
    suggestion = suggestion_context.service.generate(
        suggestion_context.conversation_id,
        trigger="manual",
    )

    assert [item["style"] for item in suggestion.suggestions] == [
        "专业说明",
        "简洁直接",
        "温和安抚",
    ]
    assert suggestion.sources
    assert suggestion.status == "success"


def test_sensitive_suggestion_cannot_be_copied(suggestion_context) -> None:
    suggestion = suggestion_context.generate_with_text("可以加微信领取优惠")

    assert suggestion.status == "blocked"
    with pytest.raises(RiskBlocked):
        suggestion_context.service.track_copy(suggestion.id)


def test_new_buyer_message_auto_generates_exactly_one_suggestion(configured_sync_context) -> None:
    event = configured_sync_context.buyer_message_event("auto-suggestion-event")
    configured_sync_context.sync_service.ingest_webhook(event.body, event.headers)
    configured_sync_context.sync_service.ingest_webhook(event.body, event.headers)

    suggestions = configured_sync_context.service.list_for_conversation(
        configured_sync_context.conversation_id
    )

    assert len([item for item in suggestions if item.trigger == "automatic"]) == 1
```

- [ ] **Step 3: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_assistant.py -v`

Expected: FAIL，因为模型网关和建议服务不存在。

- [ ] **Step 4: 实现模型与建议链路**

在 `tests/feige/conftest.py` 增加模型测试夹具：

```python
import json

import httpx

from backend.feige.integrations.mock_douyin import MockDouyinAdapter
from backend.feige.services.assistant import ModelGateway, SuggestionService
from backend.feige.services.sync import SyncService


def valid_suggestion_payload(third_text="非常理解您的心情，我来帮您核对尺码。"):
    return {
        "suggestions": [
            {"style": "专业说明", "text": "根据您的身高体重，建议选择 M 码。"},
            {"style": "简洁直接", "text": "建议 M 码，日常穿着会更舒适。"},
            {"style": "温和安抚", "text": third_text},
        ],
        "warnings": [],
    }


class SuggestionContext:
    def __init__(self, tmp_path, knowledge_service, model_content):
        self.db_path = tmp_path / "suggestion.db"
        from backend.feige.database import connect, init_database

        init_database(self.db_path)
        with connect(self.db_path) as connection:
            conversation = connection.execute(
                "SELECT id FROM conversations WHERE external_id = 'conv-demo-001'"
            ).fetchone()
        self.conversation_id = conversation["id"]
        self.model_content = model_content
        transport = httpx.MockTransport(self.handle_request)
        self.client = httpx.Client(transport=transport)
        gateway = ModelGateway(
            self.client,
            base_url="https://model.test/v1",
            model="demo-model",
            api_key="test-key",
        )
        self.service = SuggestionService(self.db_path, knowledge_service, gateway)
        self.sync_service = SyncService(
            self.db_path,
            MockDouyinAdapter(self.db_path, "webhook-secret"),
            "webhook-secret",
            suggestion_service=self.service,
        )

    def handle_request(self, request):
        content = json.dumps(self.model_content, ensure_ascii=False)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    def generate_with_text(self, text):
        self.model_content = valid_suggestion_payload(text)
        return self.service.generate(self.conversation_id, trigger="manual")

    def buyer_message_event(self, event_id):
        return make_buyer_message_event(event_id)


@pytest.fixture
def suggestion_context(tmp_path, knowledge_service):
    context = SuggestionContext(tmp_path, knowledge_service, valid_suggestion_payload())
    yield context
    context.client.close()


@pytest.fixture
def configured_sync_context(tmp_path, knowledge_service):
    context = SuggestionContext(tmp_path, knowledge_service, valid_suggestion_payload())
    yield context
    context.client.close()
```

未配置模型测试使用独立 `tmp_path` 数据库和 `SuggestionService(..., model_gateway=None)`。

模型设置：

- `base_url`
- `model_name`
- 加密 API Key
- 超时时间

调用 OpenAI 兼容 `/chat/completions`，使用 `httpx`。测试使用 `httpx.MockTransport` 返回固定 JSON，不访问真实网络。

流程：

1. 读取会话、客户、订单、SKU 和消息。
2. 调用 `KnowledgeService.retrieve`。
3. 组装包含业务事实和知识引用的消息。
4. 要求模型返回三条建议 JSON。
5. 严格校验结构和长度。
6. 检查敏感词类别：站外联系方式、微信号、QQ、手机号、站外链接。
7. 保存建议、来源和状态。
8. 成功建议允许复制，风险建议禁止复制。
9. 增加生成事件，不写入 `messages` 表。

同步服务收到新买家消息时，如果模型配置完整，调用 `SuggestionService.generate(trigger="automatic")`；异常只记录 `suggestion_failed`，不阻断消息保存或 Webhook 响应。

API：

- `POST /api/conversations/{id}/suggestions`
- `POST /api/suggestions/{id}/copy`
- `GET/PUT /api/settings/model`
- `POST /api/settings/model/test`

- [ ] **Step 5: 运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_assistant.py -v`

Expected: PASS。

```bash
git add backend/feige/services/assistant.py backend/feige/services/sync.py backend/feige/api/admin.py tests/feige/test_assistant.py
git commit -m "feat: add RAG suggestions and model gateway"
```

---

### Task 6: 中台业务分析

**Files:**
- Create: `backend/feige/services/analytics.py`
- Modify: `backend/feige/api/admin.py`
- Create: `tests/feige/test_analytics.py`

**Interfaces:**
- Consumes: 消息、建议、来源、同步和事件表。
- Produces: `AnalyticsService.snapshot() -> AnalyticsView`；`classify_consultation(text: str) -> str`。

- [ ] **Step 1: 写分类与统计失败测试**

```python
@pytest.mark.parametrize(
    ("text", "topic"),
    [
        ("身高165选什么码", "尺码"),
        ("这个面料会起球吗", "面料"),
        ("快递三天没更新", "物流"),
        ("现在有优惠吗", "价格"),
        ("怎么搭配更好看", "搭配"),
        ("我要申请退款", "售后"),
    ],
)
def test_message_topic_classification(text, topic) -> None:
    assert classify_consultation(text) == topic


def test_analytics_counts_generate_copy_and_block(analytics_context) -> None:
    payload = analytics_context.service.snapshot()

    assert payload["suggestions_generated"] >= 1
    assert payload["suggestions_copied"] >= 1
    assert payload["suggestions_blocked"] >= 1
    assert payload["webhook_failures"] >= 0
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_analytics.py -v`

Expected: FAIL，因为分析服务不存在。

- [ ] **Step 3: 实现非模型主题分类与分析**

在 `tests/feige/conftest.py` 增加分析夹具：

```python
from types import SimpleNamespace

from backend.feige.services.analytics import AnalyticsService


@pytest.fixture
def analytics_context(tmp_path):
    from backend.feige.database import connect, init_database

    db_path = tmp_path / "analytics.db"
    init_database(db_path)
    with connect(db_path) as connection:
        for event_type in (
            "suggestion_generated",
            "suggestion_generated",
            "suggestion_copied",
            "suggestion_blocked",
        ):
            connection.execute(
                "INSERT INTO analytics_events VALUES (?, ?, ?)",
                (
                    str(uuid4()),
                    event_type,
                    "2026-10-22T08:00:00+00:00",
                ),
            )
    return SimpleNamespace(service=AnalyticsService(db_path))
```

分类使用确定性关键词映射，独立于模型。

分析返回：

- `messages_today`
- `active_conversations`
- `products`、`skus`
- `orders`
- `top_topics`
- `product_mentions`
- `knowledge_hits`
- `after_sales_reasons`
- `suggestions_generated`
- `suggestions_copied`
- `suggestions_blocked`
- `webhook_failures`
- `manual_pull_count`

新增 `GET /api/analytics`。不得返回接待计时、响应率、分流或客服绩效。

- [ ] **Step 4: 运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_analytics.py -v`

Expected: PASS。

```bash
git add backend/feige/services/analytics.py backend/feige/api/admin.py tests/feige/test_analytics.py
git commit -m "feat: add middle-platform analytics"
```

---

### Task 7: Vue 路由、导航与只读提示

**Files:**
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/components/AppShell.vue`
- Create: `frontend/src/views/OverviewView.vue`
- Create: `frontend/src/views/ConversationsView.vue`
- Create: `frontend/src/views/PanelPlaceholderView.vue`
- Create: `frontend/src/views/KnowledgeView.vue`
- Create: `frontend/src/views/AnalyticsView.vue`
- Create: `frontend/src/views/SyncSettingsView.vue`
- Create: `frontend/src/views/MockEventsView.vue`
- Create: `frontend/src/components/AppShell.spec.js`

**Interfaces:**
- Consumes: 新中台 API routes。
- Produces: 导航 `概览/会话中心/商品资料/订单查询/客户档案/AI知识库/业务分析/同步与设置`；`/panel` 占位；全局“只读镜像”提示。

- [ ] **Step 1: 写导航只读测试**

```javascript
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import AppShell from './AppShell.vue'

describe('AppShell', () => {
  it('contains the Feige assist navigation and no send action', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', name: 'overview', component: { template: '<div />' } }],
    })
    await router.push('/')
    await router.isReady()
    const wrapper = mount(AppShell, {
      global: {
        plugins: [router],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })

    expect(wrapper.text()).toContain('会话中心')
    expect(wrapper.text()).toContain('AI知识库')
    expect(wrapper.text()).not.toContain('发送消息')
    expect(wrapper.text()).not.toContain('接管会话')
  })
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd frontend; npm test -- src/components/AppShell.spec.js`

Expected: FAIL，因为当前导航仍包含售后审批并缺少新页面。

- [ ] **Step 3: 重构导航与路由**

路由：

- `/` → OverviewView
- `/conversations` → ConversationsView
- `/products`
- `/orders`
- `/customers`
- `/knowledge`
- `/analytics`
- `/sync`
- `/mock-events`
- `/panel`

页面占位可以先实现为明确标题、来源说明和“此页面将在后续任务接入”的静态提示；Task 8–11 再替换为真实页面。

AppShell 增加：

- “数据镜像 · 以抖店/飞鸽为准”标记。
- 模型状态。
- 最近同步状态。
- 不显示任何发送、接管、审批入口。

- [ ] **Step 4: 运行测试并提交**

Run: `cd frontend; npm test -- src/components/AppShell.spec.js`

Expected: PASS。

```bash
git add frontend/src/router.js frontend/src/components/AppShell.vue frontend/src/components/AppShell.spec.js frontend/src/views
git commit -m "feat: switch Vue shell to Feige assist navigation"
```

---

### Task 8: 只读会话中心与 AI 建议

**Files:**
- Replace: `frontend/src/views/ConversationsView.vue`
- Create: `frontend/src/components/ReadonlyTranscript.vue`
- Create: `frontend/src/components/AiSuggestionPanel.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/styles.css`
- Delete: `frontend/src/views/ServiceView.vue`
- Create: `frontend/src/components/AiSuggestionPanel.spec.js`

**Interfaces:**
- Consumes: `GET /api/conversations`、`GET /api/conversations/{id}`、`POST /api/conversations/{id}/suggestions`、`POST /api/suggestions/{id}/copy`。
- Produces: 三栏只读会话中心；建议自动加载/重新生成/复制；无发送输入框。

- [ ] **Step 1: 写禁止发送测试**

```javascript
it('shows copy actions but no send or takeover controls', async () => {
  const wrapper = mount(AiSuggestionPanel, {
    props: {
      suggestion: {
        status: 'success',
        suggestions: [
          { style: '专业说明', text: '建议一' },
          { style: '简洁直接', text: '建议二' },
          { style: '温和安抚', text: '建议三' },
        ],
        sources: [],
      },
    },
  })

  expect(wrapper.text()).toContain('复制话术')
  expect(wrapper.text()).not.toContain('发送消息')
  expect(wrapper.text()).not.toContain('接管会话')
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd frontend; npm test -- src/components/AiSuggestionPanel.spec.js`

Expected: FAIL，因为组件不存在。

- [ ] **Step 3: 实现只读会话中心**

布局：

- 左栏：会话列表、飞鸽状态、完整性和最后同步时间。
- 中栏：纯文本消息时间线，角色标签为买家/客服/未知。
- 右栏：AI建议、订单商品、客户资料三个页签。

AI 面板：

- 当前建议、生成状态、三条话术、来源、敏感词风险。
- “重新生成”按钮。
- “复制话术”按钮调用复制统计 API。
- 未配置模型时显示前往设置。
- 模型失败时显示失败状态。

不允许页面或组件中出现 textarea 作为客服回复框。

- [ ] **Step 4: 支持刷新和轮询**

会话页面每 5 秒刷新当前会话只读数据。手动刷新按钮可见。发生自动生成的新建议时显示“新建议已生成”，不弹出发送行为。

- [ ] **Step 5: 运行测试并提交**

Run: `cd frontend; npm test -- src/components/AiSuggestionPanel.spec.js`

Expected: PASS。

```bash
git add frontend/src/views/ConversationsView.vue frontend/src/components/ReadonlyTranscript.vue frontend/src/components/AiSuggestionPanel.vue frontend/src/components/AiSuggestionPanel.spec.js frontend/src/router.js frontend/src/styles.css
git rm frontend/src/views/ServiceView.vue
git commit -m "feat: add readonly conversation center with AI suggestions"
```

---

### Task 9: 商品、SKU、订单与客户只读页面

**Files:**
- Modify: `frontend/src/views/ProductsView.vue`
- Modify: `frontend/src/views/OrdersView.vue`
- Modify: `frontend/src/views/CustomersView.vue`
- Create: `frontend/src/components/SourceFreshness.vue`
- Create: `frontend/src/views/ProductsView.spec.js`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: 只读商品、订单和客户 API，以及客户标注 API。
- Produces: 商品+SKU 详情、订单只读详情、客户本地标注编辑。

- [ ] **Step 1: 写只读商品测试**

```javascript
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'

import ProductsView from './ProductsView.vue'

afterEach(() => vi.unstubAllGlobals())

it('renders source freshness and no product edit action', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => [{
      id: 'product-1',
      title: '法式碎花连衣裙',
      category: '连衣裙',
      source: 'douyin',
      synced_at: '2026-10-22T08:00:00Z',
      skus: [{ id: 'sku-1', size: 'M', stock: 12 }],
    }],
  })))
  const wrapper = mount(ProductsView, {
    global: {
      stubs: ['RouterLink'],
      mocks: { $route: { query: {} } },
    },
  })

  await flushPromises()
  expect(wrapper.text()).toContain('抖店同步')
  expect(wrapper.text()).not.toContain('新增商品')
  expect(wrapper.text()).not.toContain('归档')
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd frontend; npm test -- src/views/ProductsView.spec.js`

Expected: FAIL，因为当前页面仍有新增、编辑和归档。

- [ ] **Step 3: 重写商品页面**

- 搜索名称、SKU、尺码、分类和库存状态。
- 商品详情展示 SKU 表格。
- 显示知识绑定状态。
- 固定只读提示。
- 删除所有新增、编辑、归档按钮和表单。

- [ ] **Step 4: 重写订单与客户页面**

订单：

- 查询订单号、客户、商品、SKU、状态和日期。
- 详情只读。
- 删除状态修改和审批入口。

客户：

- 基础资料只读。
- 标签和备注可编辑，调用 `PUT /api/customers/{id}/annotations`。
- 显示历史订单和会话。
- 显示“仅中台可见，不回写抖店”。

- [ ] **Step 5: 运行测试并提交**

Run: `cd frontend; npm test`

Expected: PASS。

```bash
git add frontend/src/views/ProductsView.vue frontend/src/views/OrdersView.vue frontend/src/views/CustomersView.vue frontend/src/components/SourceFreshness.vue frontend/src/views/ProductsView.spec.js frontend/src/styles.css
git commit -m "feat: make catalog orders and customers readonly"
```

---

### Task 10: AI 知识库页面

**Files:**
- Replace: `frontend/src/views/KnowledgeView.vue`
- Create: `frontend/src/components/KnowledgeEditor.vue`
- Create: `frontend/src/views/KnowledgeView.spec.js`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: knowledge list/create/update/delete API。
- Produces: 知识搜索、类型筛选、新增、编辑、启停和删除。

- [ ] **Step 1: 写知识库交互失败测试**

```javascript
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'

import KnowledgeView from './KnowledgeView.vue'

afterEach(() => vi.unstubAllGlobals())

it('renders knowledge types and product binding fields', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => [{
      id: 'knowledge-1',
      title: '连衣裙尺码表',
      type: '尺码表',
      content: '身高 160-165 建议 M 码',
      enabled: true,
    }],
  })))
  const wrapper = mount(KnowledgeView)
  await flushPromises()

  expect(wrapper.text()).toContain('尺码表')
  expect(wrapper.text()).toContain('面料与养护')
  expect(wrapper.find('[data-testid="knowledge-product"]').exists()).toBe(true)
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd frontend; npm test -- src/views/KnowledgeView.spec.js`

Expected: FAIL，因为知识页面仍是占位。

- [ ] **Step 3: 实现知识库界面**

- 左侧知识条目列表和筛选。
- 右侧编辑器：标题、类型、关键词、商品/分类绑定、正文、启用状态。
- 保存、停用、删除。
- 显示更新时间。
- 明确“知识库只影响中台 AI 建议，不修改抖店商品”。

- [ ] **Step 4: 运行测试并提交**

Run: `cd frontend; npm test -- src/views/KnowledgeView.spec.js`

Expected: PASS。

```bash
git add frontend/src/views/KnowledgeView.vue frontend/src/components/KnowledgeEditor.vue frontend/src/views/KnowledgeView.spec.js frontend/src/styles.css
git commit -m "feat: add local RAG knowledge management"
```

---

### Task 11: 业务分析、同步设置与模拟事件页面

**Files:**
- Replace: `frontend/src/views/AnalyticsView.vue`
- Replace: `frontend/src/views/SyncSettingsView.vue`
- Replace: `frontend/src/views/MockEventsView.vue`
- Replace: `frontend/src/views/PanelPlaceholderView.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/styles.css`
- Create: `frontend/src/views/ReadonlySafety.spec.js`

**Interfaces:**
- Consumes: analytics、integration status、model settings、manual pull、demo events API。
- Produces: 分析图表、同步状态、模拟事件表单、面板占位。

- [ ] **Step 1: 写禁用能力测试**

```javascript
it('panel placeholder has no interactive panel controls', () => {
  const wrapper = mount(PanelPlaceholderView)

  expect(wrapper.text()).toContain('飞鸽右侧 AI 辅助面板规划中')
  expect(wrapper.find('button').exists()).toBe(false)
  expect(wrapper.find('iframe').exists()).toBe(false)
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd frontend; npm test -- src/views/ReadonlySafety.spec.js`

Expected: FAIL，因为页面仍是占位或未实现。

- [ ] **Step 3: 实现分析与同步页面**

分析页：

- 高频主题。
- 商品/SKU 咨询分布。
- 知识命中。
- 售后原因。
- 建议生成、复制、拦截。
- 同步失败和手动拉取次数。

同步设置：

- 模拟 OAuth 连接状态。
- Webhook 地址和最近事件。
- 手动拉取商品/订单。
- 同步日志和最后成功时间。
- 大模型配置、Key 掩码和连接测试。

- [ ] **Step 4: 实现模拟事件和面板占位**

模拟事件表单字段：

- 事件类型。
- 外部事件 ID。
- 会话 ID。
- 买家和客服消息。
- 商品和订单变更载荷。

事件通过 `POST /api/demo/events` 进入 Webhook 同步服务。

`/panel` 只显示文字和视觉占位，没有表单、按钮或 iframe。

- [ ] **Step 5: 运行测试并提交**

Run: `cd frontend; npm test`

Expected: PASS。

```bash
git add frontend/src/views/AnalyticsView.vue frontend/src/views/SyncSettingsView.vue frontend/src/views/MockEventsView.vue frontend/src/views/PanelPlaceholderView.vue frontend/src/views/ReadonlySafety.spec.js frontend/src/router.js frontend/src/styles.css
git commit -m "feat: add analytics sync simulator and panel placeholder"
```

---

### Task 12: 切断旧可写能力并完成最终验收

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/feige/app.py`
- Delete: `frontend/src/views/ApprovalsView.vue`
- Delete: `frontend/src/views/PublicChatView.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/components/AppShell.vue`
- Modify: `start.bat`
- Modify: `README.md`
- Create: `tests/feige/test_readonly_boundary.py`
- Create: `tests/feige/test_end_to_end.py`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: 所有前序任务。
- Produces: 新应用默认入口、最终只读演示、启动脚本和说明。

- [ ] **Step 1: 写全局只读边界测试**

```python
def test_openapi_contains_no_send_or_write_routes(app) -> None:
    routes = [
        (method.upper(), route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    ]

    assert not any(
        method == "POST" and path.endswith("/messages")
        for method, path in routes
    )
    assert not any("takeover" in path for _, path in routes)
    assert not any("approval" in path for _, path in routes)
    assert not any(
        method in {"POST", "PUT", "PATCH", "DELETE"}
        and path.rstrip("/") == "/api/products"
        for method, path in routes
    )
    assert not any(
        method in {"PUT", "PATCH", "DELETE"} and "/api/products/" in path
        for method, path in routes
    )
```

- [ ] **Step 2: 写完整端到端失败测试**

```python
def test_simulated_event_updates_readonly_conversation(admin_client) -> None:
    event = admin_client.post("/api/demo/events", json={
        "event_type": "buyer_message",
        "external_event_id": "e2e-event-1",
        "external_conversation_id": "conv-e2e",
        "text": "这条裙子我身高165，应该选什么码？",
    })
    assert event.status_code == 200

    conversations = admin_client.get("/api/conversations").json()
    conversation = next(item for item in conversations if item["external_id"] == "conv-e2e")
    messages = admin_client.get(f"/api/conversations/{conversation['id']}").json()["messages"]

    assert messages[-1]["role"] == "buyer"


def test_seeded_suggestion_copy_updates_metric(admin_client) -> None:
    conversation = admin_client.get("/api/conversations").json()[0]
    detail = admin_client.get(f"/api/conversations/{conversation['id']}").json()
    suggestion = detail["suggestions"][0]
    copied = admin_client.post(f"/api/suggestions/{suggestion['id']}/copy")

    assert copied.status_code == 200
    assert admin_client.get("/api/analytics").json()["suggestions_copied"] >= 1
```

- [ ] **Step 3: 运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/feige/test_readonly_boundary.py tests/feige/test_end_to_end.py -v`

Expected: FAIL，因为旧应用仍被默认导出，且端到端流程尚未完全接通。

- [ ] **Step 4: 完成应用切换与旧能力清理**

- `backend/main.py` 只导出 `create_feige_app()` 创建的 `app`。
- 删除旧 `/api/products` 写路由、订单状态修改、会话接管、人工发送、审批和消费者聊天入口。
- 删除前端路由和按钮中的发送、接管、审批、新增/编辑商品。
- 新数据库路径为 `data/feige_assist.db`，旧 `data/demo.db` 保留不删除。
- `start.bat` 保留现有端口检测、环境检查、构建和启动能力，只把标题、演示地址和说明改成新中台。
- 不修改或删除 `docs/mockups/`。

- [ ] **Step 5: 手工验收**

Run: `start.bat --check`

Expected: 环境检查通过且不启动服务。

Run: `start.bat`

Expected: 打开登录页，默认管理员仍为 `admin / admin123`。

按以下流程验收：

1. 登录并确认导航无“售后审批”。
2. 打开 `/panel`，确认只有预留说明。
3. 进入模拟事件页，生成买家尺码咨询。
4. 会话中心出现新消息，重复提交事件不重复。
5. 在设置中配置测试模型后，自动生成三条建议。
6. 点击复制，分析页复制次数增加。
7. 商品详情显示多个 SKU 和尺码。
8. 订单详情只读。
9. 客户标签与备注可编辑，但客户姓名不可编辑。

- [ ] **Step 6: 更新 README**

必须说明：

- 飞鸽为主、中台只做建议。
- 中台没有发送能力。
- 本地模拟与真实接入边界。
- 管理员账号。
- 模拟事件流程。
- 模型配置方法。
- 商品/订单只读和客户本地标注说明。
- 当前 `/panel` 仅为占位。
- 测试命令。

- [ ] **Step 7: 最终测试与提交**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: PASS，无警告。

Run: `cd frontend; npm test`

Expected: PASS。

Run: `cd frontend; npm run build`

Expected: 成功生成生产资源。

```bash
git add backend frontend tests start.bat README.md
git commit -m "feat: deliver readonly Feige assist middle platform"
```

---

## Spec Coverage Review

| Spec requirement | Implementing tasks |
|---|---|
| 商品+SKU只读镜像 | Task 1、3、9 |
| 订单和客户只读 | Task 1、3、9 |
| 客户本地标签/备注 | Task 4、9 |
| 买家/客服消息兼容 | Task 1、2、8 |
| Webhook验签与去重 | Task 2 |
| 模拟事件走同一流程 | Task 2、11、12 |
| OAuth与只读拉取契约 | Task 2、3 |
| 本地RAG检索 | Task 4 |
| 真实模型与三条建议 | Task 5、8 |
| 自动生成一次与重新生成 | Task 5、8 |
| 敏感词禁止复制 | Task 5、8 |
| 中台独有业务分析 | Task 6、11 |
| `/panel`仅占位 | Task 7、11 |
| 无发送/接管/售后审批 | Task 3、8、12 |
| 本地启动与真实接入边界 | Task 12 |

## Execution Notes

- 旧代码只在新路径通过测试后再切走，避免重构期间丢失当前可用演示。
- 不得为了兼容旧页面而重新添加发送或写回接口。
- 如果真实抖店 API 字段与模拟适配器不同，只修改 `integrations` 层，不改变领域服务。
- 当前未提交的 `start.bat` 修改和 `docs/mockups/` 属于用户现有内容，实施时保留。
