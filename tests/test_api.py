import re

from fastapi.testclient import TestClient

from backend.main import create_app


def authenticated_client(tmp_path):
    app = create_app(db_path=tmp_path / "demo.db", session_secret="test-secret")
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    csrf_token = client.cookies.get("csrf_token")
    return client, {"X-CSRF-Token": csrf_token}


def test_health_endpoint_reports_ready(tmp_path):
    app = create_app(db_path=tmp_path / "demo.db", session_secret="test-secret")

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_products_require_login(tmp_path):
    app = create_app(db_path=tmp_path / "demo.db", session_secret="test-secret")

    response = TestClient(app).get("/api/products")

    assert response.status_code == 401


def test_demo_login_exposes_product_catalog(tmp_path):
    client, _ = authenticated_client(tmp_path)

    response = client.get("/api/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 5
    assert {"id", "name", "price_cents", "stock", "status"} <= set(products[0])


def test_product_edit_updates_database(tmp_path):
    client, headers = authenticated_client(tmp_path)
    product = client.get("/api/products").json()[0]

    response = client.put(
        f"/api/products/{product['id']}",
        headers=headers,
        json={"name": "晨雾香氛（演示修改）", "price_cents": 16900},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "晨雾香氛（演示修改）"
    assert response.json()["price_cents"] == 16900


def test_dashboard_returns_merchant_metrics(tmp_path):
    client, _ = authenticated_client(tmp_path)

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_count"] >= 5
    assert payload["order_count"] >= 1
    assert len(payload["recent_orders"]) >= 1


def test_mutating_request_rejects_missing_csrf(tmp_path):
    client, _ = authenticated_client(tmp_path)
    product = client.get("/api/products").json()[0]

    response = client.put(
        f"/api/products/{product['id']}",
        json={"name": "不应保存"},
    )

    assert response.status_code == 403


def test_conversation_supports_manual_reply_and_takeover(tmp_path):
    client, headers = authenticated_client(tmp_path)
    conversation = client.get("/api/conversations").json()[0]

    response = client.post(
        f"/api/conversations/{conversation['id']}/takeover",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "human"

    reply = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        headers=headers,
        json={"text": "您好，我来继续为您处理。", "role": "human"},
    )
    assert reply.status_code == 201
    assert reply.json()["role"] == "human"


def test_pending_approval_can_be_approved(tmp_path):
    client, headers = authenticated_client(tmp_path)
    approvals = client.get("/api/approvals?status=pending").json()

    response = client.post(
        f"/api/approvals/{approvals[0]['id']}/decision",
        headers=headers,
        json={"decision": "approve", "note": "演示审批通过"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_spa_fallback_serves_index_when_frontend_is_built(tmp_path):
    app = create_app(db_path=tmp_path / "demo.db", session_secret="test-secret")
    client = TestClient(app)

    response = client.get("/products")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert re.search(r"<div id=\"app\"></div>", response.text)
