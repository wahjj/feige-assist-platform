from typing import Annotated

from fastapi import APIRouter, Depends, Request

from backend.feige.auth import require_admin as _require_admin
from backend.feige.auth import require_csrf
from backend.feige.services.read_queries import ReadQueries
from backend.feige.services.sync import SyncService


def build_admin_router(
    read_queries: ReadQueries,
    sync_service: SyncService,
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

    return router
