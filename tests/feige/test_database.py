from pathlib import Path

from backend.feige.database import connect, init_database


def test_seed_contains_product_with_multiple_skus(tmp_path: Path) -> None:
    db_path = tmp_path / "feige.db"
    init_database(db_path)

    with connect(db_path) as connection:
        product = connection.execute(
            "SELECT id, title, source FROM products LIMIT 1"
        ).fetchone()
        skus = connection.execute(
            "SELECT sku_name, size, price_cents, stock FROM product_skus WHERE product_id = ?",
            (product["id"],),
        ).fetchall()

    assert product["source"] == "douyin"
    assert product["title"]
    assert len(skus) >= 2
    assert skus[0]["size"]
    assert skus[0]["price_cents"] > 0


def test_seed_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "feige.db"
    init_database(db_path)

    with connect(db_path) as connection:
        first_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    init_database(db_path)

    with connect(db_path) as connection:
        second_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    assert first_count == second_count
