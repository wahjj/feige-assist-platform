from uuid import uuid4


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


def test_readonly_states_cannot_be_changed(admin_client) -> None:
    order = admin_client.get("/api/orders").json()[0]

    response = admin_client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "已完成"},
    )

    assert response.status_code in {404, 405}


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


def test_login_required(admin_client) -> None:
    admin_client.cookies.clear()

    response = admin_client.get("/api/products")

    assert response.status_code == 401
