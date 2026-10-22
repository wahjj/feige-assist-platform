import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.database import connect, init_database, utc_now, verify_password


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "demo.db"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


class LoginRequest(BaseModel):
    username: str
    password: str


class ProductPayload(BaseModel):
    name: str | None = None
    category: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    status: str | None = None
    emoji: str | None = None
    accent: str | None = None
    description: str | None = None
    sku: str | None = None


class CustomerPayload(BaseModel):
    name: str | None = None
    phone: str | None = None
    tags: list[str] | str | None = None
    note: str | None = None


class MessagePayload(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    role: str = "human"


class ApprovalDecisionPayload(BaseModel):
    decision: str
    note: str = ""


class ModelSettingsPayload(BaseModel):
    base_url: str = ""
    model: str = ""
    api_key: str = ""


class OrderStatusPayload(BaseModel):
    status: str


class SyncProductItem(BaseModel):
    external_id: str
    name: str
    category: str = "未分类"
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)
    status: str = "上架"
    description: str = ""


class SyncCustomerItem(BaseModel):
    external_id: str
    name: str
    phone: str
    tags: list[str] = Field(default_factory=list)
    note: str = ""


def make_session_token(secret: str, username: str) -> str:
    expires = int(time.time()) + 12 * 60 * 60
    payload = f"{username}|{expires}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def read_session_token(secret: str, token: str | None) -> str | None:
    if not token or token.count("|") != 2:
        return None
    username, expires_text, signature = token.split("|")
    try:
        expires = int(expires_text)
    except ValueError:
        return None
    if expires < int(time.time()):
        return None
    payload = f"{username}|{expires_text}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return username


def tags_to_list(value: str) -> list[str]:
    return [item for item in value.split("、") if item]


def product_from_row(row: sqlite3.Row) -> dict:
    payload = dict(row)
    payload["price"] = payload["price_cents"] / 100
    payload["archived"] = bool(payload["archived"])
    return payload


def customer_from_row(row: sqlite3.Row) -> dict:
    payload = dict(row)
    payload["tags"] = tags_to_list(payload["tags"])
    payload["phone_masked"] = mask_phone(payload["phone"])
    return payload


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def customer_metrics(connection: sqlite3.Connection, customer_id: str) -> dict:
    row = connection.execute(
        """
        SELECT
            COUNT(*) AS order_count,
            COALESCE(SUM(CASE WHEN status IN ('待发货', '已发货', '已完成')
                THEN total_cents ELSE 0 END), 0) AS total_spent
        FROM orders
        WHERE customer_id = ? AND status != '已取消'
        """,
        (customer_id,),
    ).fetchone()
    return {"order_count": row["order_count"], "total_spent_cents": row["total_spent"]}


def build_demo_ai_reply(text: str, order_no: str | None) -> tuple[str, str]:
    if any(word in text for word in ("人工", "投诉", "曝光")):
        return "我理解您的心情，正在为您转接人工客服，请稍候。", "待人工"
    if any(word in text for word in ("补偿", "退款", "赔付")):
        target = f"订单 {order_no}" if order_no else "您的订单"
        return f"已记录您对{target}的售后诉求，并提交商家审核，审核后会尽快同步结果。", "待审批"
    if any(word in text for word in ("物流", "快递", "发货")):
        target = f"订单 {order_no} " if order_no else ""
        return (
            f"我查到{target}目前物流在运输中，最近更新为“运输中”。"
            "我已记录您的催件诉求，会继续跟进并尽快同步进展。",
            "AI处理中",
        )
    if any(word in text for word in ("香", "味道", "气味")):
        return "晨雾无火香氛是雪松与白茶的木质调，气味柔和，适合卧室和书房。", "AI处理中"
    if any(word in text for word in ("库存", "现货", "还有吗")):
        return "您好，这款目前有现货，工作日下午四点前下单通常可以当天发出。", "AI处理中"
    return "您好，我已经收到您的问题。为了更准确地帮您处理，请补充订单号或具体需求。", "AI处理中"


def call_real_model(settings: dict, text: str, recent_messages: list[dict]) -> str:
    base_url = settings.get("model_base_url", "").rstrip("/")
    model = settings.get("model_name", "")
    api_key = settings.get("model_api_key", "")
    if not base_url or not model or not api_key:
        raise RuntimeError("大模型尚未配置")
    messages = [
        {
            "role": "system",
            "content": (
                "你是电商店铺的客服助手。只根据提供的商品、订单和会话信息回答；"
                "不得编造物流或订单状态；退款、补偿、补发必须说明将提交人工审核。"
            ),
        },
        *recent_messages[-10:],
        {"role": "user", "content": text},
    ]
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.2},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def create_app(
    db_path: Path | None = None,
    session_secret: str = "local-demo-session-secret",
) -> FastAPI:
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    init_database(resolved_db)

    app = FastAPI(title="禾光商家中心 Demo", version="0.1.0")
    app.state.db_path = resolved_db
    app.state.session_secret = session_secret
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def db() -> sqlite3.Connection:
        return connect(resolved_db)

    def require_admin(request: Request) -> str:
        username = read_session_token(
            session_secret,
            request.cookies.get("admin_session"),
        )
        if not username:
            raise HTTPException(status_code=401, detail="请先登录")
        return username

    def require_csrf(request: Request) -> None:
        cookie_token = request.cookies.get("csrf_token", "")
        header_token = request.headers.get("X-CSRF-Token", "")
        if not cookie_token or not hmac.compare_digest(cookie_token, header_token):
            raise HTTPException(status_code=403, detail="CSRF 校验失败")

    def require_sync_key(request: Request) -> None:
        with db() as connection:
            row = connection.execute(
                "SELECT value FROM app_settings WHERE key = 'sync_api_key'"
            ).fetchone()
        configured = row["value"] if row else ""
        authorization = request.headers.get("Authorization", "")
        supplied = authorization.removeprefix("Bearer ").strip()
        if not configured or not hmac.compare_digest(configured, supplied):
            raise HTTPException(status_code=401, detail="同步密钥无效")

    def settings_dict(connection: sqlite3.Connection) -> dict[str, str]:
        return {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key, value FROM app_settings")
        }

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, response: Response) -> dict:
        with db() as connection:
            row = connection.execute(
                "SELECT username, password_hash, password_salt FROM admins WHERE username = ?",
                (payload.username,),
            ).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"], row["password_salt"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        token = make_session_token(session_secret, row["username"])
        csrf_token = secrets.token_urlsafe(24)
        response.set_cookie(
            "admin_session",
            token,
            httponly=True,
            samesite="lax",
            max_age=12 * 60 * 60,
        )
        response.set_cookie(
            "csrf_token",
            csrf_token,
            httponly=False,
            samesite="lax",
            max_age=12 * 60 * 60,
        )
        return {"authenticated": True, "username": row["username"], "csrf_token": csrf_token}

    @app.post("/api/auth/logout")
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie("admin_session")
        response.delete_cookie("csrf_token")
        return {"ok": True}

    @app.get("/api/auth/session")
    def session(request: Request) -> dict:
        username = read_session_token(
            session_secret,
            request.cookies.get("admin_session"),
        )
        return {
            "authenticated": bool(username),
            "username": username,
            "csrf_token": request.cookies.get("csrf_token", ""),
        }

    @app.get("/api/dashboard")
    def dashboard(_: Annotated[str, Depends(require_admin)]) -> dict:
        with db() as connection:
            product_count = connection.execute(
                "SELECT COUNT(*) FROM products WHERE archived = 0"
            ).fetchone()[0]
            order_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            customer_count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            pending_count = connection.execute(
                "SELECT COUNT(*) FROM approvals WHERE status = 'pending'"
            ).fetchone()[0]
            active_conversations = connection.execute(
                "SELECT COUNT(*) FROM conversations WHERE status != '已结束'"
            ).fetchone()[0]
            revenue = connection.execute(
                """
                SELECT COALESCE(SUM(total_cents), 0) FROM orders
                WHERE status IN ('待发货', '已发货', '已完成')
                """
            ).fetchone()[0]
            recent_rows = connection.execute(
                """
                SELECT o.id, o.order_no, o.status, o.total_cents, o.created_at,
                       c.name AS customer_name
                FROM orders o JOIN customers c ON c.id = o.customer_id
                ORDER BY o.created_at DESC LIMIT 5
                """
            ).fetchall()
            status_rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM orders GROUP BY status"
            ).fetchall()
            category_rows = connection.execute(
                """
                SELECT category, COUNT(*) AS count FROM products
                WHERE archived = 0 GROUP BY category ORDER BY count DESC
                """
            ).fetchall()
        return {
            "product_count": product_count,
            "order_count": order_count,
            "customer_count": customer_count,
            "pending_approval_count": pending_count,
            "active_conversation_count": active_conversations,
            "revenue_cents": revenue,
            "recent_orders": [dict(row) for row in recent_rows],
            "order_statuses": [dict(row) for row in status_rows],
            "categories": [dict(row) for row in category_rows],
            "sales_trend": [
                {"label": "10/16", "value": 1820},
                {"label": "10/17", "value": 2460},
                {"label": "10/18", "value": 2180},
                {"label": "10/19", "value": 3610},
                {"label": "10/20", "value": 2940},
                {"label": "10/21", "value": 4380},
                {"label": "今日", "value": 3260},
            ],
        }

    @app.get("/api/products")
    def list_products(
        _: Annotated[str, Depends(require_admin)],
        q: str = "",
        status: str = "",
    ) -> list[dict]:
        clauses = ["archived = 0"]
        params: list[str] = []
        if q:
            clauses.append("(name LIKE ? OR sku LIKE ? OR category LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like])
        if status:
            clauses.append("status = ?")
            params.append(status)
        query = f"SELECT * FROM products WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC"
        with db() as connection:
            rows = connection.execute(query, params).fetchall()
        return [product_from_row(row) for row in rows]

    @app.post("/api/products", status_code=201)
    def create_product(
        payload: ProductPayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        if not payload.name or payload.price_cents is None or payload.stock is None:
            raise HTTPException(status_code=422, detail="名称、价格和库存必填")
        now = utc_now()
        product_id = str(uuid4())
        with db() as connection:
            connection.execute(
                """
                INSERT INTO products (
                    id, external_id, name, sku, category, price_cents, stock, status,
                    emoji, accent, description, archived, created_at, updated_at
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    product_id,
                    payload.name,
                    payload.sku or f"HX-{product_id[:4].upper()}",
                    payload.category or "未分类",
                    payload.price_cents,
                    payload.stock,
                    payload.status or "上架",
                    payload.emoji or "📦",
                    payload.accent or "#e5eadf",
                    payload.description or "",
                    now,
                    now,
                ),
            )
            row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return product_from_row(row)

    @app.put("/api/products/{product_id}")
    def update_product(
        product_id: str,
        payload: ProductPayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        fields = payload.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=422, detail="没有可更新的字段")
        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with db() as connection:
            cursor = connection.execute(
                f"UPDATE products SET {assignments} WHERE id = ?",
                [*fields.values(), product_id],
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="商品不存在")
            row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return product_from_row(row)

    @app.delete("/api/products/{product_id}")
    def archive_product(
        product_id: str,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict[str, bool]:
        with db() as connection:
            connection.execute(
                "UPDATE products SET archived = 1, status = '已归档', updated_at = ? WHERE id = ?",
                (utc_now(), product_id),
            )
        return {"ok": True}

    @app.get("/api/orders")
    def list_orders(_: Annotated[str, Depends(require_admin)]) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                """
                SELECT o.*, c.name AS customer_name,
                       (SELECT COALESCE(SUM(quantity), 0) FROM order_items WHERE order_id = o.id)
                           AS item_count
                FROM orders o JOIN customers c ON c.id = o.customer_id
                ORDER BY o.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    @app.get("/api/orders/{order_id}")
    def order_detail(
        order_id: str,
        _: Annotated[str, Depends(require_admin)],
    ) -> dict:
        with db() as connection:
            order = connection.execute(
                """
                SELECT o.*, c.name AS customer_name, c.id AS customer_id
                FROM orders o JOIN customers c ON c.id = o.customer_id
                WHERE o.id = ?
                """,
                (order_id,),
            ).fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")
            items = connection.execute(
                "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
            ).fetchall()
        return {**dict(order), "items": [dict(row) for row in items]}

    @app.patch("/api/orders/{order_id}/status")
    def update_order_status(
        order_id: str,
        payload: OrderStatusPayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        allowed = {"待付款", "待发货", "已发货", "已完成", "已取消"}
        if payload.status not in allowed:
            raise HTTPException(status_code=422, detail="订单状态无效")
        with db() as connection:
            cursor = connection.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (payload.status, utc_now(), order_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="订单不存在")
            row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return dict(row)

    @app.get("/api/customers")
    def list_customers(
        _: Annotated[str, Depends(require_admin)],
        q: str = "",
        tag: str = "",
    ) -> list[dict]:
        clauses = []
        params: list[str] = []
        if q:
            clauses.append("(name LIKE ? OR phone LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])
        if tag:
            clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with db() as connection:
            rows = connection.execute(
                f"SELECT * FROM customers {where} ORDER BY created_at DESC", params
            ).fetchall()
            customers = []
            for row in rows:
                customer = customer_from_row(row)
                customer.update(customer_metrics(connection, row["id"]))
                customers.append(customer)
        return customers

    @app.get("/api/customers/{customer_id}")
    def customer_detail(
        customer_id: str,
        _: Annotated[str, Depends(require_admin)],
    ) -> dict:
        with db() as connection:
            row = connection.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="客户不存在")
            customer = customer_from_row(row)
            customer.update(customer_metrics(connection, customer_id))
            orders = connection.execute(
                "SELECT id, order_no, status, total_cents, created_at FROM orders WHERE customer_id = ? ORDER BY created_at DESC",
                (customer_id,),
            ).fetchall()
            conversations = connection.execute(
                "SELECT id, subject, status, last_message, updated_at FROM conversations WHERE customer_id = ? ORDER BY updated_at DESC",
                (customer_id,),
            ).fetchall()
        return {
            **customer,
            "orders": [dict(item) for item in orders],
            "conversations": [dict(item) for item in conversations],
        }

    @app.put("/api/customers/{customer_id}")
    def update_customer(
        customer_id: str,
        payload: CustomerPayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        fields = payload.model_dump(exclude_none=True)
        if "tags" in fields:
            fields["tags"] = (
                "、".join(fields["tags"])
                if isinstance(fields["tags"], list)
                else fields["tags"]
            )
        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with db() as connection:
            connection.execute(
                f"UPDATE customers SET {assignments} WHERE id = ?",
                [*fields.values(), customer_id],
            )
            row = connection.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return customer_from_row(row)

    @app.get("/api/conversations")
    def list_conversations(_: Annotated[str, Depends(require_admin)]) -> list[dict]:
        with db() as connection:
            rows = connection.execute(
                """
                SELECT cv.*, c.name AS customer_name, c.phone AS customer_phone,
                       o.order_no, o.status AS order_status
                FROM conversations cv
                JOIN customers c ON c.id = cv.customer_id
                LEFT JOIN orders o ON o.id = cv.order_id
                ORDER BY cv.updated_at DESC
                """
            ).fetchall()
        payload = []
        for row in rows:
            item = dict(row)
            item["customer_phone"] = mask_phone(item["customer_phone"])
            payload.append(item)
        return payload

    @app.get("/api/conversations/{conversation_id}")
    def conversation_detail(
        conversation_id: str,
        _: Annotated[str, Depends(require_admin)],
    ) -> dict:
        with db() as connection:
            conversation = connection.execute(
                """
                SELECT cv.*, c.name AS customer_name, c.phone AS customer_phone,
                       c.tags AS customer_tags, o.order_no, o.status AS order_status,
                       o.logistics_status, o.total_cents
                FROM conversations cv
                JOIN customers c ON c.id = cv.customer_id
                LEFT JOIN orders o ON o.id = cv.order_id
                WHERE cv.id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
            messages = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            ).fetchall()
        payload = dict(conversation)
        payload["customer_phone"] = mask_phone(payload["customer_phone"])
        payload["customer_tags"] = tags_to_list(payload["customer_tags"])
        payload["messages"] = [dict(row) for row in messages]
        return payload

    @app.post("/api/conversations/{conversation_id}/takeover")
    def takeover_conversation(
        conversation_id: str,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        with db() as connection:
            connection.execute(
                "UPDATE conversations SET status = 'human', updated_at = ? WHERE id = ?",
                (utc_now(), conversation_id),
            )
            row = connection.execute(
                "SELECT id, status FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="会话不存在")
        return dict(row)

    @app.post("/api/conversations/{conversation_id}/messages", status_code=201)
    def send_manual_message(
        conversation_id: str,
        payload: MessagePayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        with db() as connection:
            conversation = connection.execute(
                "SELECT status FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
            if conversation["status"] != "human":
                raise HTTPException(status_code=409, detail="请先接管会话")
            message_id = str(uuid4())
            now = utc_now()
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
                (message_id, conversation_id, "human", payload.text, now),
            )
            connection.execute(
                "UPDATE conversations SET last_message = ?, unread = 0, updated_at = ? WHERE id = ?",
                (payload.text, now, conversation_id),
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": "human",
            "text": payload.text,
            "created_at": now,
        }

    @app.get("/api/approvals")
    def list_approvals(
        _: Annotated[str, Depends(require_admin)],
        status: str = Query(default=""),
    ) -> list[dict]:
        where = "WHERE a.status = ?" if status else ""
        params = [status] if status else []
        with db() as connection:
            rows = connection.execute(
                f"""
                SELECT a.*, c.name AS customer_name, o.order_no, o.logistics_status
                FROM approvals a
                JOIN conversations cv ON cv.id = a.conversation_id
                JOIN customers c ON c.id = cv.customer_id
                JOIN orders o ON o.id = a.order_id
                {where}
                ORDER BY a.created_at DESC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    @app.post("/api/approvals/{approval_id}/decision")
    def decide_approval(
        approval_id: str,
        payload: ApprovalDecisionPayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        if payload.decision not in {"approve", "reject"}:
            raise HTTPException(status_code=422, detail="审批决定无效")
        next_status = "approved" if payload.decision == "approve" else "rejected"
        with db() as connection:
            cursor = connection.execute(
                """
                UPDATE approvals SET status = ?, note = ?, updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (next_status, payload.note, utc_now(), approval_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=409, detail="审批已处理")
            row = connection.execute(
                "SELECT * FROM approvals WHERE id = ?", (approval_id,)
            ).fetchone()
        return dict(row)

    @app.get("/api/settings")
    def get_settings(_: Annotated[str, Depends(require_admin)]) -> dict:
        with db() as connection:
            settings = settings_dict(connection)
            logs = connection.execute(
                "SELECT * FROM sync_logs ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        key = settings.get("model_api_key", "")
        sync_key = settings.get("sync_api_key", "")
        return {
            "shop_name": settings.get("shop_name", ""),
            "shop_slogan": settings.get("shop_slogan", ""),
            "model_base_url": settings.get("model_base_url", ""),
            "model_name": settings.get("model_name", ""),
            "model_api_key_masked": f"••••••••{key[-4:]}" if key else "尚未配置",
            "model_configured": bool(key and settings.get("model_base_url")),
            "sync_api_key_masked": f"{sync_key[:4]}••••••••{sync_key[-4:]}"
            if len(sync_key) > 8
            else "••••••••",
            "sync_base_url": "http://127.0.0.1:8000/api/sync/v1",
            "sync_last_at": logs[0]["created_at"] if logs else "",
            "sync_logs": [dict(row) for row in logs],
        }

    @app.put("/api/settings/model")
    def update_model_settings(
        payload: ModelSettingsPayload,
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict[str, bool]:
        values = {
            "model_base_url": payload.base_url.strip(),
            "model_name": payload.model.strip(),
        }
        if payload.api_key.strip():
            values["model_api_key"] = payload.api_key.strip()
        with db() as connection:
            connection.executemany(
                """
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                values.items(),
            )
        return {"ok": True}

    @app.post("/api/settings/model/test")
    def test_model_settings(
        _: Annotated[str, Depends(require_admin)],
        __: Annotated[None, Depends(require_csrf)],
    ) -> dict:
        with db() as connection:
            settings = settings_dict(connection)
        if not settings.get("model_api_key"):
            raise HTTPException(status_code=400, detail="请先保存大模型 API Key")
        try:
            answer = call_real_model(
                settings,
                "请只回复：连接成功",
                [],
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"连接失败：{exc}") from exc
        return {"ok": True, "preview": answer[:120]}

    @app.post("/api/sync/v1/products")
    def sync_products(
        records: list[SyncProductItem],
        _: Annotated[None, Depends(require_sync_key)],
    ) -> dict:
        results = []
        now = utc_now()
        with db() as connection:
            for item in records:
                product_id = str(uuid4())
                try:
                    connection.execute(
                        """
                        INSERT INTO products (
                            id, external_id, name, sku, category, price_cents, stock, status,
                            emoji, accent, description, archived, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                        ON CONFLICT(external_id) DO UPDATE SET
                            name = excluded.name,
                            category = excluded.category,
                            price_cents = excluded.price_cents,
                            stock = excluded.stock,
                            status = excluded.status,
                            description = excluded.description,
                            updated_at = excluded.updated_at
                        """,
                        (
                            product_id,
                            item.external_id,
                            item.name,
                            f"SYNC-{item.external_id}",
                            item.category,
                            item.price_cents,
                            item.stock,
                            item.status,
                            "📦",
                            "#e7e7df",
                            item.description,
                            now,
                            now,
                        ),
                    )
                    results.append({"external_id": item.external_id, "status": "ok"})
                except Exception as exc:
                    results.append(
                        {"external_id": item.external_id, "status": "error", "error": str(exc)}
                    )
            connection.execute(
                "INSERT INTO sync_logs VALUES (?, ?, ?, ?)",
                (
                    str(uuid4()),
                    "/api/sync/v1/products",
                    f"成功 {sum(item['status'] == 'ok' for item in results)} 条",
                    now,
                ),
            )
        return {"results": results}

    @app.post("/api/public/chat/start")
    def start_public_chat() -> dict:
        with db() as connection:
            customer = connection.execute(
                "SELECT id, name FROM customers ORDER BY created_at LIMIT 1"
            ).fetchone()
            order = connection.execute(
                "SELECT id, order_no FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT 1",
                (customer["id"],),
            ).fetchone()
            conversation_id = str(uuid4())
            now = utc_now()
            connection.execute(
                """
                INSERT INTO conversations (
                    id, external_id, customer_id, order_id, status, subject,
                    last_message, unread, updated_at
                ) VALUES (?, NULL, ?, ?, 'AI处理中', '售前售后咨询', '欢迎咨询', 0, ?)
                """,
                (conversation_id, customer["id"], order["id"], now),
            )
        return {"conversation_id": conversation_id}

    @app.get("/api/public/chat/{conversation_id}")
    def public_chat_detail(conversation_id: str) -> dict:
        with db() as connection:
            messages = connection.execute(
                "SELECT role, text, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            ).fetchall()
            conversation = connection.execute(
                "SELECT status FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"status": conversation["status"], "messages": [dict(row) for row in messages]}

    @app.post("/api/public/chat/{conversation_id}/messages", status_code=201)
    def public_chat_message(conversation_id: str, payload: MessagePayload) -> dict:
        now = utc_now()
        with db() as connection:
            conversation = connection.execute(
                """
                SELECT cv.id, cv.status, cv.order_id, o.order_no
                FROM conversations cv LEFT JOIN orders o ON o.id = cv.order_id
                WHERE cv.id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, 'customer', ?, ?)",
                (str(uuid4()), conversation_id, payload.text, now),
            )
            history = connection.execute(
                "SELECT role, text FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 10",
                (conversation_id,),
            ).fetchall()
            settings = settings_dict(connection)

        reply, next_status = build_demo_ai_reply(payload.text, conversation["order_no"])
        if settings.get("model_api_key"):
            try:
                reply = call_real_model(settings, payload.text, [dict(item) for item in history])
            except Exception:
                reply = "目前大模型服务暂时不可用，正在为您转接人工客服。"
                next_status = "待人工"

        reply_time = utc_now()
        with db() as connection:
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, 'ai', ?, ?)",
                (str(uuid4()), conversation_id, reply, reply_time),
            )
            connection.execute(
                "UPDATE conversations SET last_message = ?, status = ?, updated_at = ? WHERE id = ?",
                (reply, next_status, reply_time, conversation_id),
            )
            if next_status == "待审批" and conversation["order_id"]:
                connection.execute(
                    """
                    INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', '', ?, ?)
                    """,
                    (
                        str(uuid4()),
                        conversation_id,
                        conversation["order_id"],
                        "退款补偿",
                        3000,
                        "消费者通过在线客服提出补偿诉求",
                        "聊天工作台自动生成，等待商家核验",
                        reply_time,
                        reply_time,
                    ),
                )
        return {"reply": reply, "status": next_status}

    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index_file = FRONTEND_DIST / "index.html"
        if not index_file.exists():
            return HTMLResponse(
                "<h1>前端尚未构建</h1><p>请运行 npm install 和 npm run build。</p>",
                status_code=503,
            )
        return FileResponse(index_file)

    return app


app = create_app()
