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
