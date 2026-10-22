import hashlib
import hmac
import json


def test_signed_douyin_webhook_endpoint_accepts_message(app) -> None:
    from fastapi.testclient import TestClient

    payload = {
        "event_id": "real-webhook-shape-1",
        "event_type": "buyer_message",
        "external_conversation_id": "conv-demo-001",
        "external_message_id": "real-webhook-message-1",
        "role": "buyer",
        "message_type": "text",
        "text": "这个面料会起球吗？",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = hmac.new(b"demo-webhook-secret", body, hashlib.sha256).hexdigest()

    response = TestClient(app).post(
        "/integrations/doudian/feige/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Event-ID": "real-webhook-shape-1",
            "X-Signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
