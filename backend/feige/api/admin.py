from typing import Annotated
import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Request

from backend.feige.auth import require_admin as _require_admin
from backend.feige.auth import require_csrf
from backend.feige.database import connect
from backend.feige.services.annotations import AnnotationService
from backend.feige.services.analytics import AnalyticsService
from backend.feige.services.assistant import SuggestionService
from backend.feige.services.knowledge import KnowledgeService
from backend.feige.services.read_queries import ReadQueries
from backend.feige.services.sync import SyncService


def build_admin_router(
    read_queries: ReadQueries,
    sync_service: SyncService,
    annotation_service: AnnotationService,
    knowledge_service: KnowledgeService,
    suggestion_service: SuggestionService,
    analytics_service: AnalyticsService,
    session_secret: str,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    def current_admin(request: Request) -> str:
        return _require_admin(request, session_secret)

    Admin = Annotated[str, Depends(current_admin)]
    Csrf = Annotated[None, Depends(require_csrf)]

    @router.get("/dashboard")
    def dashboard(_: Admin) -> dict:
        return read_queries.dashboard()

    @router.get("/products")
    def products(_: Admin, q: str = "", category: str = "") -> list[dict]:
        return read_queries.list_products(q, category)

    @router.get("/products/{product_id}")
    def product(product_id: str, _: Admin) -> dict:
        return read_queries.product_detail(product_id)

    @router.get("/orders")
    def orders(_: Admin, q: str = "") -> list[dict]:
        return read_queries.list_orders(q)

    @router.get("/orders/{order_id}")
    def order(order_id: str, _: Admin) -> dict:
        return read_queries.order_detail(order_id)

    @router.get("/customers")
    def customers(_: Admin, q: str = "", tag: str = "") -> list[dict]:
        return read_queries.list_customers(q, tag)

    @router.get("/customers/{customer_id}")
    def customer(customer_id: str, _: Admin) -> dict:
        return read_queries.customer_detail(customer_id)

    @router.put("/customers/{customer_id}/annotations")
    def update_annotation(
        customer_id: str,
        payload: dict,
        admin: Admin,
        __: Csrf,
    ) -> dict:
        return annotation_service.update(
            customer_id,
            tags=payload.get("tags", []),
            note=payload.get("note", ""),
            actor=admin,
        )

    @router.get("/conversations")
    def conversations(_: Admin, state: str = "") -> list[dict]:
        return read_queries.list_conversations(state)

    @router.get("/conversations/{conversation_id}")
    def conversation(conversation_id: str, _: Admin) -> dict:
        return read_queries.conversation_detail(conversation_id)

    @router.get("/integration/status")
    def integration_status(_: Admin) -> dict:
        return read_queries.integration_status()

    @router.post("/integration/pull/products")
    def pull_products(_: Admin, __: Csrf) -> dict:
        return sync_service.pull_products().model_dump()

    @router.post("/integration/pull/orders")
    def pull_orders(_: Admin, __: Csrf) -> dict:
        return sync_service.pull_orders().model_dump()

    @router.get("/knowledge")
    def knowledge(_: Admin, q: str = "", entry_type: str = "") -> list[dict]:
        return knowledge_service.list_entries(q, entry_type)

    @router.post("/knowledge", status_code=201)
    def create_knowledge(_: Admin, __: Csrf, payload: dict) -> dict:
        return knowledge_service.create(payload)

    @router.put("/knowledge/{entry_id}")
    def update_knowledge(
        entry_id: str,
        payload: dict,
        _: Admin,
        __: Csrf,
    ) -> dict:
        return knowledge_service.update(entry_id, payload)

    @router.delete("/knowledge/{entry_id}", status_code=204)
    def delete_knowledge(entry_id: str, _: Admin, __: Csrf) -> None:
        knowledge_service.delete(entry_id)

    @router.post("/conversations/{conversation_id}/suggestions")
    def generate_suggestion(
        conversation_id: str,
        _: Admin,
        __: Csrf,
    ) -> dict:
        return suggestion_service.generate(
            conversation_id,
            trigger="manual",
        ).model_dump(mode="json")

    @router.post("/suggestions/{suggestion_id}/copy")
    def copy_suggestion(
        suggestion_id: str,
        _: Admin,
        __: Csrf,
    ) -> dict:
        return suggestion_service.track_copy(suggestion_id)

    @router.get("/settings/model")
    def get_model_settings(_: Admin) -> dict:
        with connect(read_queries.db_path) as connection:
            settings = {
                row["key"]: row["value"]
                for row in connection.execute(
                    """
                    SELECT key, value FROM app_settings
                    WHERE key IN ('model_base_url', 'model_name', 'model_api_key')
                    """
                )
            }
        key = settings.get("model_api_key", "")
        return {
            "base_url": settings.get("model_base_url", ""),
            "model_name": settings.get("model_name", ""),
            "api_key_masked": f"••••••••{key[-4:]}" if key else "尚未配置",
            "configured": bool(
                settings.get("model_base_url")
                and settings.get("model_name")
                and key
            ),
        }

    @router.put("/settings/model")
    def update_model_settings(
        payload: dict,
        _: Admin,
        __: Csrf,
    ) -> dict[str, bool]:
        values = {
            "model_base_url": payload.get("base_url", "").strip(),
            "model_name": payload.get("model_name", "").strip(),
        }
        if payload.get("api_key", "").strip():
            values["model_api_key"] = payload["api_key"].strip()
        with connect(read_queries.db_path) as connection:
            connection.executemany(
                """
                INSERT INTO app_settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                values.items(),
            )
        return {"ok": True}

    @router.post("/settings/model/test")
    def test_model_settings(_: Admin, __: Csrf) -> dict:
        return suggestion_service.test_connection()

    @router.get("/analytics")
    def analytics(_: Admin) -> dict:
        return analytics_service.snapshot()

    @router.post("/demo/events")
    def demo_event(
        payload: dict,
        _: Admin,
        __: Csrf,
    ) -> dict:
        event_id = payload.get("external_event_id")
        if not event_id:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="external_event_id 必填")
        body_payload = {**payload, "event_id": event_id}
        raw_body = json.dumps(body_payload, ensure_ascii=False).encode("utf-8")
        signature = hmac.new(
            sync_service.webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        result = sync_service.ingest_webhook(
            raw_body,
            {
                "X-Event-ID": event_id,
                "X-Signature": signature,
            },
        )
        return result.model_dump(mode="json")

    return router
