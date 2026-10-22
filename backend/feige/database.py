from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        resolved_salt.encode("ascii"),
        210_000,
    ).hex()
    return digest, resolved_salt


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_accounts (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shop_connections (
    id TEXT PRIMARY KEY,
    shop_external_id TEXT NOT NULL UNIQUE,
    shop_name TEXT NOT NULL,
    app_key TEXT NOT NULL DEFAULT '',
    encrypted_token TEXT NOT NULL DEFAULT '',
    connection_status TEXT NOT NULL,
    authorized_at TEXT,
    token_updated_at TEXT,
    last_product_sync_at TEXT,
    last_order_sync_at TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    image_emoji TEXT NOT NULL,
    status TEXT NOT NULL,
    fabric TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'douyin',
    synced_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_skus (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '',
    size TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL,
    stock INTEGER NOT NULL,
    synced_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_skus_product ON product_skus(product_id);

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'douyin',
    synced_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_annotations (
    customer_id TEXT PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    tags_json TEXT NOT NULL DEFAULT '[]',
    note TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    order_no TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL,
    logistics_status TEXT NOT NULL DEFAULT '暂无物流',
    after_sales_status TEXT NOT NULL DEFAULT '无',
    source TEXT NOT NULL DEFAULT 'douyin',
    created_at TEXT NOT NULL,
    synced_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);

CREATE TABLE IF NOT EXISTS order_items (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id),
    sku_id TEXT NOT NULL REFERENCES product_skus(id),
    product_name TEXT NOT NULL,
    sku_name TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    order_id TEXT REFERENCES orders(id),
    state TEXT NOT NULL,
    completeness TEXT NOT NULL,
    subject TEXT NOT NULL,
    last_message TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    synced_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('buyer', 'service_agent', 'unknown')),
    message_type TEXT NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    synced_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, sent_at);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id TEXT PRIMARY KEY,
    entry_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '',
    product_id TEXT REFERENCES products(id),
    category TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_product ON knowledge_entries(product_id);

CREATE TABLE IF NOT EXISTS suggestions (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    context_summary TEXT NOT NULL,
    model_name TEXT NOT NULL,
    status TEXT NOT NULL,
    suggestions_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    trigger_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    copied_count INTEGER NOT NULL DEFAULT 0,
    last_copied_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_suggestions_conversation ON suggestions(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS suggestion_sources (
    id TEXT PRIMARY KEY,
    suggestion_id TEXT NOT NULL REFERENCES suggestions(id) ON DELETE CASCADE,
    knowledge_id TEXT REFERENCES knowledge_entries(id),
    product_id TEXT REFERENCES products(id),
    sku_id TEXT REFERENCES product_skus(id),
    title TEXT NOT NULL,
    rank INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    signature_valid INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    received_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id TEXT PRIMARY KEY,
    sync_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    success_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    error_summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_database(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '2')"
        )
        seed_demo(connection)


def seed_demo(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
        return

    now = datetime.now(UTC).replace(microsecond=0)
    created_at = (now - timedelta(days=45)).isoformat()
    synced_at = now.isoformat()
    password_hash, password_salt = hash_password("admin123")
    connection.execute(
        "INSERT INTO admin_accounts VALUES (?, ?, ?, ?, ?)",
        (str(uuid4()), "admin", password_hash, password_salt, created_at),
    )
    connection.execute(
        """
        INSERT INTO shop_connections (
            id, shop_external_id, shop_name, app_key, encrypted_token,
            connection_status, authorized_at, token_updated_at,
            last_product_sync_at, last_order_sync_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            "demo-shop-001",
            "禾光女装旗舰店",
            "demo-app-key",
            "demo-token-placeholder",
            "demo_connected",
            synced_at,
            synced_at,
            synced_at,
            synced_at,
        ),
    )

    product_specs = [
        (
            "法式收腰碎花连衣裙",
            "连衣裙",
            "👗",
            "在售",
            "100%聚酯纤维，雪纺内衬，建议冷水轻柔手洗",
            [("雾蓝 S", "雾蓝", "S", 26900, 18), ("雾蓝 M", "雾蓝", "M", 26900, 24), ("雾蓝 L", "雾蓝", "L", 26900, 13)],
        ),
        (
            "轻羊毛通勤针织开衫",
            "针织衫",
            "🧶",
            "在售",
            "45%羊毛 55%腈纶，亲肤柔软，平铺晾干",
            [("燕麦 S", "燕麦", "S", 32900, 9), ("燕麦 M", "燕麦", "M", 32900, 16), ("深灰 M", "深灰", "M", 32900, 11)],
        ),
        (
            "高腰垂感阔腿西裤",
            "裤装",
            "👖",
            "在售",
            "88%聚酯纤维 12%氨纶，垂顺不易皱",
            [("黑色 M", "黑色", "M", 23900, 21), ("黑色 L", "黑色", "L", 23900, 15), ("卡其 M", "卡其", "M", 23900, 7)],
        ),
        (
            "轻薄防晒短外套",
            "外套",
            "🧥",
            "在售",
            "锦纶防晒面料，UPF50+，可机洗",
            [("奶油白 S", "奶油白", "S", 19900, 28), ("奶油白 M", "奶油白", "M", 19900, 31), ("雾粉 M", "雾粉", "M", 19900, 12)],
        ),
        (
            "丝光棉基础圆领 T 恤",
            "T恤",
            "👚",
            "在售",
            "新疆长绒棉，丝光处理，不易变形",
            [("白色 M", "白色", "M", 12900, 46), ("白色 L", "白色", "L", 12900, 33), ("黑色 M", "黑色", "M", 12900, 25)],
        ),
        (
            "复古格纹半身裙",
            "半身裙",
            "🥻",
            "下架",
            "羊毛混纺格纹面料，内里顺滑",
            [("棕格 S", "棕格", "S", 25900, 4), ("棕格 M", "棕格", "M", 25900, 6)],
        ),
    ]
    product_ids: dict[str, str] = {}
    sku_ids: dict[str, str] = {}
    for product_index, (title, category, emoji, status, fabric, skus) in enumerate(product_specs):
        product_id = str(uuid4())
        external_id = f"product-{product_index + 1:03d}"
        product_ids[external_id] = product_id
        connection.execute(
            """
            INSERT INTO products (
                id, external_id, title, category, image_emoji, status,
                fabric, source, synced_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'douyin', ?, ?)
            """,
            (
                product_id,
                external_id,
                title,
                category,
                emoji,
                status,
                fabric,
                synced_at,
                created_at,
            ),
        )
        for sku_index, (sku_name, color, size, price_cents, stock) in enumerate(skus):
            sku_id = str(uuid4())
            sku_external_id = f"sku-{product_index + 1:03d}-{sku_index + 1:02d}"
            sku_ids[sku_external_id] = sku_id
            connection.execute(
                """
                INSERT INTO product_skus (
                    id, external_id, product_id, sku_name, color, size,
                    price_cents, stock, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sku_id,
                    sku_external_id,
                    product_id,
                    sku_name,
                    color,
                    size,
                    price_cents,
                    stock,
                    synced_at,
                ),
            )

    customer_specs = [
        ("林予安", "13800132218", ["高复购", "尺码咨询"], "偏好法式通勤风，常穿 M 码。"),
        ("周南乔", "13622190432", ["新客"], "首次咨询连衣裙尺码。"),
        ("顾清禾", "15988034216", ["高客单", "面料敏感"], "关注羊毛与贴肤面料。"),
        ("沈知夏", "13755220981", ["礼赠"], "节日期间会购买多件。"),
        ("陈屿", "18633092177", ["待跟进"], "咨询过断货商品。" ),
    ]
    customer_ids: list[str] = []
    for index, (name, phone, tags, note) in enumerate(customer_specs):
        customer_id = str(uuid4())
        customer_ids.append(customer_id)
        connection.execute(
            """
            INSERT INTO customers VALUES (?, ?, ?, ?, 'douyin', ?, ?)
            """,
            (
                customer_id,
                f"customer-{index + 1:03d}",
                name,
                phone,
                synced_at,
                created_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO customer_annotations VALUES (?, ?, ?, 'admin', ?)
            """,
            (customer_id, json.dumps(tags, ensure_ascii=False), note, synced_at),
        )

    order_specs = [
        (0, "245.00", "待发货", "等待揽收", "无", 1, "sku-001-02", "雾蓝 M"),
        (2, "329.00", "已发货", "运输中", "无", 5, "sku-002-01", "燕麦 S"),
        (3, "269.00", "已完成", "已签收", "无", 9, "sku-001-01", "雾蓝 S"),
        (1, "199.00", "待付款", "暂无物流", "无", 0, "sku-004-03", "雾粉 M"),
        (4, "129.00", "已完成", "已签收", "退款关闭", 17, "sku-005-01", "白色 M"),
        (2, "239.00", "已完成", "已签收", "无", 24, "sku-003-01", "黑色 M"),
    ]
    order_ids: list[str] = []
    for index, (customer_index, amount, status, logistics, after_sales, days_ago, sku_external, sku_name) in enumerate(order_specs):
        order_id = str(uuid4())
        order_ids.append(order_id)
        product_external = f"product-{int(sku_external.split('-')[1]):03d}"
        product_id = product_ids[product_external]
        sku_id = sku_ids[sku_external]
        created_order = (now - timedelta(days=days_ago)).isoformat()
        amount_cents = int(float(amount) * 100)
        connection.execute(
            """
            INSERT INTO orders (
                id, external_id, order_no, customer_id, amount_cents, status,
                logistics_status, after_sales_status, source, created_at, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'douyin', ?, ?)
            """,
            (
                order_id,
                f"order-{index + 1:03d}",
                f"HG202610{22 - index:02d}{index + 1:04d}",
                customer_ids[customer_index],
                amount_cents,
                status,
                logistics,
                after_sales,
                created_order,
                synced_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                str(uuid4()),
                f"order-item-{index + 1:03d}",
                order_id,
                product_id,
                sku_id,
                product_specs[int(product_external.split('-')[1]) - 1][0],
                sku_name,
                amount_cents,
            ),
        )

    conversation_specs = [
        ("conv-demo-001", 0, 0, "接待中", "complete", "连衣裙尺码咨询", 2),
        ("conv-demo-002", 1, 3, "接待中", "buyer_only", "防晒衣颜色咨询", 5),
        ("conv-demo-003", 2, 1, "已关闭", "complete", "羊毛开衫售后咨询", 0),
        ("conv-demo-004", 3, 2, "已关闭", "complete", "礼服搭配咨询", 0),
    ]
    conversation_ids: dict[str, str] = {}
    for index, (external_id, customer_index, order_index, state, completeness, subject, unread) in enumerate(conversation_specs):
        conversation_id = str(uuid4())
        conversation_ids[external_id] = conversation_id
        last_message = [
            "我身高 165、体重 52kg，连衣裙选哪个码？",
            "雾粉 M 码还有现货吗？",
            "开衫洗完后有点缩水，可以怎么处理？",
            "这套搭配有同色系包包推荐吗？",
        ][index]
        updated = (now - timedelta(minutes=index * 13 + 3)).isoformat()
        connection.execute(
            """
            INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                external_id,
                customer_ids[customer_index],
                order_ids[order_index],
                state,
                completeness,
                subject,
                last_message,
                updated,
                synced_at,
            ),
        )
        role = "buyer"
        if completeness == "complete":
            message_specs = [
                ("buyer", "你好，我身高 165、体重 52kg，这条连衣裙选哪个码？"),
                ("service_agent", "您好，这款版型偏宽松，建议 M 码，腰围更舒适。"),
                ("buyer", "我平时穿 L 码，会不会 M 太小？"),
                ("service_agent", "这款胸围余量较大，M 码建议胸围 88-94cm。"),
            ] if index == 0 else [
                ("buyer", "开衫洗完后有点缩水，可以怎么处理？"),
                ("service_agent", "羊毛混纺不建议机洗，可以平铺蒸汽熨烫恢复。"),
            ] if index == 2 else [
                ("buyer", "这套搭配有同色系包包推荐吗？"),
                ("service_agent", "可以搭配奶白色小方包，整体会更轻盈。"),
            ]
        else:
            message_specs = [
                ("buyer", "雾粉 M 码还有现货吗？"),
                ("buyer", "如果现在下单大概什么时候发货？"),
            ]
        for message_index, (message_role, content) in enumerate(message_specs):
            sent_at = (now - timedelta(minutes=(len(message_specs) - message_index) * 2 + index)).isoformat()
            connection.execute(
                """
                INSERT INTO messages VALUES (?, ?, ?, ?, 'text', ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    f"msg-demo-{index + 1:02d}-{message_index + 1:02d}",
                    conversation_id,
                    message_role,
                    content,
                    sent_at,
                    synced_at,
                ),
            )

    knowledge_specs = [
        ("尺码表", "法式连衣裙尺码建议", "身高 160-168cm、体重 50-55kg 通常建议 M 码。胸围 88-94cm 可选 M 码。", "尺码,身高,体重,连衣裙,M码", "product-001", "连衣裙"),
        ("面料与养护", "雪纺连衣裙清洗说明", "冷水轻柔手洗，不可漂白，悬挂阴干。建议使用洗衣袋。", "雪纺,清洗,养护,起球", "product-001", "连衣裙"),
        ("通用规则", "服装尺码测量方式", "尺码以平铺测量为准，手工测量可能存在 1-3cm 误差。", "尺码,误差,测量", None, "通用"),
        ("面料与养护", "羊毛针织防缩水", "建议冷水手洗或干洗，不可拧干，平铺晾干。", "羊毛,缩水,洗护,开衫", "product-002", "针织衫"),
        ("搭配建议", "雾蓝连衣裙搭配", "可搭配奶白小方包与米色浅口鞋，适合通勤和约会。", "搭配,包包,鞋子,通勤", "product-001", "连衣裙"),
        ("售后规则", "服装七日无理由说明", "不影响二次销售的商品支持七日无理由退货，具体以订单售后页为准。", "退款,退货,售后,七天", None, "售后"),
        ("常见问答", "防晒衣洗护", "可机洗，建议使用中性洗涤剂，避免高温烘干。", "防晒衣,机洗,洗护", "product-004", "外套"),
        ("常见问答", " T 恤会透吗", "丝光棉为中等厚度，浅色建议搭配肤色内衣。", "T恤,白色,透", "product-005", "T恤"),
        ("售后规则", "颜色差异说明", "不同显示设备可能有轻微色差，不属于质量问题。", "色差,颜色,售后", None, "售后"),
        ("尺码表", "高腰西裤尺码建议", "腰围 68-72cm 建议 M 码，裤长适合 160-170cm。", "西裤,腰围,裤长,尺码", "product-003", "裤装"),
    ]
    knowledge_ids: list[str] = []
    for index, (entry_type, title, content, keywords, product_external, category) in enumerate(knowledge_specs):
        knowledge_id = str(uuid4())
        knowledge_ids.append(knowledge_id)
        connection.execute(
            """
            INSERT INTO knowledge_entries (
                id, entry_type, title, content, keywords, product_id, category,
                enabled, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
            """,
            (
                knowledge_id,
                entry_type,
                title,
                content,
                keywords,
                product_ids.get(product_external) if product_external else None,
                category,
                created_at,
                synced_at,
            ),
        )

    history_suggestions = [
        (
            conversation_ids["conv-demo-001"],
            [
                {"style": "专业说明", "text": "根据您 165cm、52kg 的身材数据，这款连衣裙建议选择 M 码。"},
                {"style": "简洁直接", "text": "建议选 M 码，胸围和腰围会更合适。"},
                {"style": "温和安抚", "text": "您平时穿 L 码也不用太担心，这款版型偏宽松，M 码更显腰线。"},
            ],
            [knowledge_ids[0], knowledge_ids[1]],
        ),
        (
            conversation_ids["conv-demo-003"],
            [
                {"style": "专业说明", "text": "羊毛混纺缩水后可以尝试低温蒸汽熨烫恢复。"},
                {"style": "简洁直接", "text": "不要机洗，建议用蒸汽熨烫后平铺晾干。"},
                {"style": "温和安抚", "text": "非常理解您的担心，我可以把洗护步骤发给您参考。"},
            ],
            [knowledge_ids[3]],
        ),
    ]
    for conversation_id, suggestions, source_ids in history_suggestions:
        suggestion_id = str(uuid4())
        created_suggestion = (now - timedelta(hours=2)).isoformat()
        connection.execute(
            """
            INSERT INTO suggestions VALUES (?, ?, ?, ?, 'success', ?, '[]', 'automatic', ?, 1, ?)
            """,
            (
                suggestion_id,
                conversation_id,
                "根据当前会话、关联订单和服装知识库生成",
                "demo-model",
                json.dumps(suggestions, ensure_ascii=False),
                created_suggestion,
                created_suggestion,
            ),
        )
        for rank, knowledge_id in enumerate(source_ids, start=1):
            entry = connection.execute(
                "SELECT title, product_id FROM knowledge_entries WHERE id = ?",
                (knowledge_id,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO suggestion_sources VALUES (?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    str(uuid4()),
                    suggestion_id,
                    knowledge_id,
                    entry["product_id"],
                    entry["title"],
                    rank,
                ),
            )

    connection.execute(
        "INSERT INTO sync_runs VALUES (?, 'products', ?, ?, 6, 0, '')",
        (str(uuid4()), synced_at, synced_at),
    )
    connection.execute(
        "INSERT INTO sync_runs VALUES (?, 'orders', ?, ?, 6, 0, '')",
        (str(uuid4()), synced_at, synced_at),
    )
    connection.executemany(
        "INSERT INTO analytics_events VALUES (?, ?, ?, ?)",
        [
            (str(uuid4()), "suggestion_generated", "{}", (now - timedelta(minutes=18)).isoformat()),
            (str(uuid4()), "suggestion_generated", "{}", (now - timedelta(minutes=12)).isoformat()),
            (str(uuid4()), "suggestion_copied", "{}", (now - timedelta(minutes=10)).isoformat()),
            (str(uuid4()), "suggestion_blocked", '{"category":"offsite_contact"}', (now - timedelta(minutes=30)).isoformat()),
        ],
    )
    settings = {
        "shop_name": "禾光女装旗舰店",
        "model_base_url": "",
        "model_name": "",
        "model_api_key": "",
        "webhook_secret": "demo-webhook-secret",
        "last_webhook_at": synced_at,
    }
    connection.executemany(
        "INSERT INTO app_settings(key, value) VALUES (?, ?)",
        settings.items(),
    )
