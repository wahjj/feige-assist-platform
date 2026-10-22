import pytest


def test_suggestion_fails_cleanly_when_model_is_not_configured(tmp_path) -> None:
    from backend.feige.database import connect, init_database
    from backend.feige.services.assistant import ModelNotConfigured, SuggestionService
    from backend.feige.services.knowledge import KnowledgeService

    db_path = tmp_path / "unconfigured.db"
    init_database(db_path)
    with connect(db_path) as connection:
        conversation_id = connection.execute(
            "SELECT id FROM conversations LIMIT 1"
        ).fetchone()["id"]
    suggestion_service = SuggestionService(
        db_path,
        KnowledgeService(db_path),
        model_gateway=None,
    )
    before = suggestion_service.list_for_conversation(conversation_id)

    with pytest.raises(ModelNotConfigured):
        suggestion_service.generate(conversation_id, trigger="manual")

    assert suggestion_service.list_for_conversation(conversation_id) == before


def test_suggestion_contains_three_styles_and_sources(suggestion_context) -> None:
    suggestion = suggestion_context.service.generate(
        suggestion_context.conversation_id,
        trigger="manual",
    )

    assert [item.style for item in suggestion.suggestions] == [
        "专业说明",
        "简洁直接",
        "温和安抚",
    ]
    assert suggestion.sources
    assert suggestion.status == "success"


def test_sensitive_suggestion_cannot_be_copied(suggestion_context) -> None:
    suggestion = suggestion_context.generate_with_text("可以加微信领取优惠")

    assert suggestion.status == "blocked"
    from backend.feige.services.assistant import RiskBlocked

    with pytest.raises(RiskBlocked):
        suggestion_context.service.track_copy(suggestion.id)


def test_new_buyer_message_auto_generates_exactly_one_suggestion(
    configured_sync_context,
) -> None:
    event = configured_sync_context.buyer_message_event("auto-suggestion-event")
    configured_sync_context.sync_service.ingest_webhook(event.body, event.headers)
    configured_sync_context.sync_service.ingest_webhook(event.body, event.headers)

    suggestions = configured_sync_context.service.list_for_conversation(
        configured_sync_context.conversation_id
    )

    assert len([item for item in suggestions if item.trigger == "automatic"]) == 1
