def test_webhook_event_is_processed_only_once(sync_context) -> None:
    event = sync_context.buyer_message_event("event-001")

    first = sync_context.service.ingest_webhook(event.body, event.headers)
    second = sync_context.service.ingest_webhook(event.body, event.headers)

    assert first.status == "accepted"
    assert second.status == "duplicate"
    with sync_context.connect() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM messages WHERE external_id = ?",
                ("msg-001",),
            ).fetchone()[0]
            == 1
        )


def test_invalid_signature_is_rejected(sync_context) -> None:
    event = sync_context.buyer_message_event("event-002", valid_signature=False)

    result = sync_context.service.ingest_webhook(event.body, event.headers)

    assert result.status == "invalid_signature"


def test_pull_products_upserts_skus_without_writeback(sync_context) -> None:
    result = sync_context.service.pull_products()

    assert result.success_count >= 6
    assert result.failed_count == 0
    assert not hasattr(sync_context.adapter, "update_product")


def test_pull_orders_updates_readonly_snapshot(sync_context) -> None:
    result = sync_context.service.pull_orders()

    assert result.success_count >= 6
    assert result.failed_count == 0
    assert not hasattr(sync_context.adapter, "update_order")
