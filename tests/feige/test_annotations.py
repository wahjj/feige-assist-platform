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
