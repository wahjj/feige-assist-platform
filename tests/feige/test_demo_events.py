def test_demo_buyer_event_uses_webhook_ingestion(admin_client) -> None:
    response = admin_client.post(
        "/api/demo/events",
        json={
            "event_type": "buyer_message",
            "external_event_id": "demo-ui-event-1",
            "external_conversation_id": "conv-demo-001",
            "external_message_id": "demo-ui-message-1",
            "text": "请问这条裙子 165 身高选什么码？",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    conversations = admin_client.get("/api/conversations").json()
    conversation = next(
        item for item in conversations if item["external_id"] == "conv-demo-001"
    )
    detail = admin_client.get(f"/api/conversations/{conversation['id']}").json()
    assert detail["messages"][-1]["content"] == "请问这条裙子 165 身高选什么码？"


def test_duplicate_demo_event_is_ignored(admin_client) -> None:
    payload = {
        "event_type": "buyer_message",
        "external_event_id": "demo-ui-event-duplicate",
        "external_conversation_id": "conv-demo-001",
        "external_message_id": "demo-ui-message-duplicate",
        "text": "重复消息",
    }

    first = admin_client.post("/api/demo/events", json=payload)
    second = admin_client.post("/api/demo/events", json=payload)

    assert first.json()["status"] == "accepted"
    assert second.json()["status"] == "duplicate"
