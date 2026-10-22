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


def test_customer_annotation_is_only_writable_business_resource(admin_client) -> None:
    customer = admin_client.get("/api/customers").json()[0]

    assert admin_client.put(
        f"/api/customers/{customer['id']}/annotations",
        json={"tags": ["本地标注"], "note": "只在中台可见"},
    ).status_code == 200
    assert admin_client.patch(
        f"/api/orders/{customer['id']}/status",
        json={"status": "已完成"},
    ).status_code in {404, 405}
