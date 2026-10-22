import pytest

from backend.feige.services.analytics import classify_consultation


@pytest.mark.parametrize(
    ("text", "topic"),
    [
        ("身高165选什么码", "尺码"),
        ("这个面料会起球吗", "面料"),
        ("快递三天没更新", "物流"),
        ("现在有优惠吗", "价格"),
        ("怎么搭配更好看", "搭配"),
        ("我要申请退款", "售后"),
    ],
)
def test_message_topic_classification(text, topic) -> None:
    assert classify_consultation(text) == topic


def test_analytics_counts_generate_copy_and_block(analytics_context) -> None:
    payload = analytics_context.service.snapshot()

    assert payload["suggestions_generated"] >= 3
    assert payload["suggestions_copied"] >= 2
    assert payload["suggestions_blocked"] >= 2
    assert payload["webhook_failures"] >= 0
    assert "top_topics" in payload
