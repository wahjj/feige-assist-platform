import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.feige.database import connect, init_database
from backend.feige.integrations.mock_douyin import MockDouyinAdapter
from backend.feige.services.sync import SyncService


@dataclass
class SignedEvent:
    body: bytes
    headers: dict[str, str]


def make_buyer_message_event(
    event_id: str,
    valid_signature: bool = True,
) -> SignedEvent:
    payload = {
        "event_id": event_id,
        "event_type": "buyer_message",
        "external_conversation_id": "conv-demo-001",
        "external_message_id": "msg-001",
        "role": "buyer",
        "message_type": "text",
        "text": "这条裙子我身高165，应该选什么码？",
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    if not valid_signature:
        signature = "invalid"
    return SignedEvent(
        body=body,
        headers={"X-Event-ID": event_id, "X-Signature": signature},
    )


class SyncContext:
    def __init__(self, tmp_path: Path) -> None:
        self.db_path = tmp_path / "feige.db"
        init_database(self.db_path)
        self.adapter = MockDouyinAdapter(self.db_path, "webhook-secret")
        self.service = SyncService(self.db_path, self.adapter, "webhook-secret")

    def connect(self):
        return connect(self.db_path)

    def buyer_message_event(
        self,
        event_id: str,
        valid_signature: bool = True,
    ) -> SignedEvent:
        return make_buyer_message_event(event_id, valid_signature)


@pytest.fixture
def sync_context(tmp_path):
    return SyncContext(tmp_path)


@pytest.fixture
def app(tmp_path):
    from backend.feige.app import create_feige_app

    return create_feige_app(
        db_path=tmp_path / "feige-api.db",
        session_secret="test-secret",
    )


@pytest.fixture
def admin_client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        client.headers.update({"X-CSRF-Token": client.cookies["csrf_token"]})
        yield client


@pytest.fixture
def knowledge_service(tmp_path):
    from backend.feige.database import init_database
    from backend.feige.services.knowledge import KnowledgeService

    db_path = tmp_path / "knowledge.db"
    init_database(db_path)
    return KnowledgeService(db_path)


@pytest.fixture
def seeded_ids(tmp_path):
    db_path = tmp_path / "knowledge.db"
    init_database(db_path)
    with connect(db_path) as connection:
        product = connection.execute(
            "SELECT id, category FROM products ORDER BY created_at LIMIT 1"
        ).fetchone()
    return {"product_id": product["id"], "category": product["category"]}


def valid_suggestion_payload(third_text="非常理解您的心情，我来帮您核对尺码。"):
    return {
        "suggestions": [
            {"style": "专业说明", "text": "根据您的身高体重，建议选择 M 码。"},
            {"style": "简洁直接", "text": "建议 M 码，日常穿着会更舒适。"},
            {"style": "温和安抚", "text": third_text},
        ],
        "warnings": [],
    }


class SuggestionContext:
    def __init__(self, tmp_path: Path, model_content):
        import httpx

        from backend.feige.integrations.mock_douyin import MockDouyinAdapter
        from backend.feige.services.assistant import ModelGateway, SuggestionService
        from backend.feige.services.knowledge import KnowledgeService
        from backend.feige.services.sync import SyncService

        self.db_path = tmp_path / "suggestion.db"
        init_database(self.db_path)
        with connect(self.db_path) as connection:
            conversation = connection.execute(
                "SELECT id FROM conversations WHERE external_id = 'conv-demo-001'"
            ).fetchone()
        self.conversation_id = conversation["id"]
        self.model_content = model_content
        transport = httpx.MockTransport(self.handle_request)
        self.client = httpx.Client(transport=transport)
        gateway = ModelGateway(
            self.client,
            base_url="https://model.test/v1",
            model="demo-model",
            api_key="test-key",
        )
        self.service = SuggestionService(
            self.db_path,
            KnowledgeService(self.db_path),
            gateway,
        )
        self.sync_service = SyncService(
            self.db_path,
            MockDouyinAdapter(self.db_path, "webhook-secret"),
            "webhook-secret",
            suggestion_service=self.service,
        )

    def handle_request(self, request):
        import httpx

        content = json.dumps(self.model_content, ensure_ascii=False)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    def generate_with_text(self, text):
        self.model_content = valid_suggestion_payload(text)
        return self.service.generate(self.conversation_id, trigger="manual")

    def buyer_message_event(self, event_id):
        return make_buyer_message_event(event_id)


@pytest.fixture
def suggestion_context(tmp_path, knowledge_service):
    context = SuggestionContext(tmp_path, valid_suggestion_payload())
    yield context
    context.client.close()


@pytest.fixture
def configured_sync_context(tmp_path, knowledge_service):
    context = SuggestionContext(tmp_path, valid_suggestion_payload())
    yield context
    context.client.close()


@pytest.fixture
def analytics_context(tmp_path):
    from types import SimpleNamespace
    from uuid import uuid4

    from backend.feige.database import connect, init_database
    from backend.feige.services.analytics import AnalyticsService

    db_path = tmp_path / "analytics.db"
    init_database(db_path)
    with connect(db_path) as connection:
        for event_type in (
            "suggestion_generated",
            "suggestion_generated",
            "suggestion_copied",
            "suggestion_blocked",
        ):
            connection.execute(
                "INSERT INTO analytics_events VALUES (?, ?, ?, ?)",
                (
                    str(uuid4()),
                    event_type,
                    "{}",
                    "2026-10-22T08:00:00+00:00",
                ),
            )
    return SimpleNamespace(service=AnalyticsService(db_path))
