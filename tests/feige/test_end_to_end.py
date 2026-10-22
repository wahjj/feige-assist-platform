def test_simulated_event_updates_readonly_conversation(admin_client) -> None:
    event = admin_client.post(
        "/api/demo/events",
        json={
            "event_type": "buyer_message",
            "external_event_id": "e2e-event-1",
            "external_conversation_id": "conv-demo-001",
            "external_message_id": "e2e-message-1",
            "text": "这条裙子我身高165，应该选什么码？",
        },
    )
    assert event.status_code == 200

    conversations = admin_client.get("/api/conversations").json()
    conversation = next(
        item for item in conversations if item["external_id"] == "conv-demo-001"
    )
    detail = admin_client.get(f"/api/conversations/{conversation['id']}").json()

    assert detail["messages"][-1]["role"] == "buyer"
    assert detail["messages"][-1]["content"] == "这条裙子我身高165，应该选什么码？"


def test_seeded_suggestion_copy_updates_metric(admin_client) -> None:
    conversation = admin_client.get("/api/conversations").json()[0]
    detail = admin_client.get(f"/api/conversations/{conversation['id']}").json()
    suggestion = detail["suggestions"][0]

    copied = admin_client.post(f"/api/suggestions/{suggestion['id']}/copy")
    analytics = admin_client.get("/api/analytics").json()

    assert copied.status_code == 200
    assert copied.json()["sent_to_buyer"] is False
    assert analytics["suggestions_copied"] >= 1


def test_model_endpoint_is_not_configured_by_default(admin_client) -> None:
    payload = admin_client.get("/api/settings/model").json()

    assert payload["configured"] is False
    assert payload["api_key_masked"] == "尚未配置"
