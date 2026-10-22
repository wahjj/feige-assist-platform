def test_product_bound_knowledge_ranks_before_general(
    knowledge_service,
    seeded_ids,
) -> None:
    hits = knowledge_service.retrieve(
        query="这条裙子偏大吗，身高 165 怎么选",
        product_id=seeded_ids["product_id"],
        category=seeded_ids["category"],
        limit=5,
    )

    assert len(hits) <= 5
    assert str(hits[0].product_id) == seeded_ids["product_id"]
    assert "尺码" in hits[0].title


def test_knowledge_can_be_created_and_disabled(knowledge_service) -> None:
    created = knowledge_service.create(
        {
            "entry_type": "常见问答",
            "title": "连衣裙口袋说明",
            "content": "连衣裙两侧有隐形口袋。",
            "keywords": "口袋,连衣裙",
            "product_id": None,
            "category": "连衣裙",
            "enabled": True,
        }
    )

    assert created["enabled"] is True
    disabled = knowledge_service.update(
        created["id"],
        {"enabled": False},
    )
    assert disabled["enabled"] is False
