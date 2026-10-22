from __future__ import annotations

from collections import Counter
from pathlib import Path

from backend.feige.database import connect


TOPIC_RULES = [
    ("尺码", ("尺码", "码数", "选什么码", "身高", "体重", "偏大", "偏小")),
    ("面料", ("面料", "起球", "羊毛", "雪纺", "材质", "缩水", "洗护")),
    ("物流", ("物流", "快递", "发货", "揽收", "运单", "到货")),
    ("价格", ("价格", "优惠", "便宜", "折扣", "券", "多少钱")),
    ("搭配", ("搭配", "配什么", "包包", "鞋子", "风格")),
    ("售后", ("退款", "退货", "售后", "补偿", "换货", "投诉")),
]


def classify_consultation(text: str) -> str:
    for topic, words in TOPIC_RULES:
        if any(word in text for word in words):
            return topic
    return "其他"


class AnalyticsService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def snapshot(self) -> dict:
        with connect(self.db_path) as connection:
            buyer_messages = connection.execute(
                "SELECT content FROM messages WHERE role = 'buyer'"
            ).fetchall()
            topic_counts = Counter(
                classify_consultation(message["content"])
                for message in buyer_messages
            )
            event_counts = Counter(
                row["event_type"]
                for row in connection.execute(
                    "SELECT event_type FROM analytics_events"
                )
            )
            knowledge_hits = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT k.title, k.entry_type, COUNT(*) AS hits
                    FROM suggestion_sources s
                    JOIN knowledge_entries k ON k.id = s.knowledge_id
                    GROUP BY k.id
                    ORDER BY hits DESC, k.title
                    LIMIT 8
                    """
                )
            ]
            product_mentions = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT p.title, p.category, COUNT(DISTINCT cv.id) AS conversations
                    FROM conversations cv
                    JOIN orders o ON o.id = cv.order_id
                    JOIN order_items oi ON oi.order_id = o.id
                    JOIN products p ON p.id = oi.product_id
                    GROUP BY p.id
                    ORDER BY conversations DESC, p.title
                    LIMIT 8
                    """
                )
            ]
            after_sales = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT after_sales_status AS reason, COUNT(*) AS count
                    FROM orders WHERE after_sales_status != '无'
                    GROUP BY after_sales_status ORDER BY count DESC
                    """
                )
            ]
            webhook_failures = connection.execute(
                """
                SELECT COUNT(*) FROM webhook_events
                WHERE status IN ('invalid_signature', 'processing_error')
                """
            ).fetchone()[0]
            manual_pulls = connection.execute(
                "SELECT COUNT(*) FROM sync_runs"
            ).fetchone()[0]
            messages_today = connection.execute(
                "SELECT COUNT(*) FROM messages WHERE date(sent_at) = date('now')"
            ).fetchone()[0]
            active_conversations = connection.execute(
                "SELECT COUNT(*) FROM conversations WHERE state != '已关闭'"
            ).fetchone()[0]

        return {
            "messages_today": messages_today,
            "active_conversations": active_conversations,
            "top_topics": [
                {"topic": topic, "count": count}
                for topic, count in topic_counts.most_common()
            ],
            "product_mentions": product_mentions,
            "knowledge_hits": knowledge_hits,
            "after_sales_reasons": after_sales,
            "suggestions_generated": event_counts["suggestion_generated"],
            "suggestions_copied": event_counts["suggestion_copied"],
            "suggestions_blocked": event_counts["suggestion_blocked"],
            "webhook_failures": webhook_failures,
            "manual_pull_count": manual_pulls,
            "feige_performance_included": False,
        }
