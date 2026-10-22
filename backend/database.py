from __future__ import annotations

import hashlib
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


def verify_password(password: str, digest: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return secrets.compare_digest(candidate, digest)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    name TEXT NOT NULL,
    sku TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    stock INTEGER NOT NULL,
    status TEXT NOT NULL,
    emoji TEXT NOT NULL,
    accent TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    tags TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    order_no TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    receiver TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    status TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    logistics_company TEXT NOT NULL DEFAULT '',
    tracking_no TEXT NOT NULL DEFAULT '',
    logistics_status TEXT NOT NULL DEFAULT '暂无物流',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    emoji TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    order_id TEXT REFERENCES orders(id),
    status TEXT NOT NULL,
    subject TEXT NOT NULL,
    last_message TEXT NOT NULL,
    unread INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    order_id TEXT NOT NULL REFERENCES orders(id),
    action_type TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    reason TEXT NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_database(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        _seed_demo(connection)


def _seed_demo(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if existing:
        return

    now = datetime.now(UTC).replace(microsecond=0)
    created = now - timedelta(days=35)
    created_text = created.isoformat()
    updated_text = now.isoformat()
    password_hash, password_salt = hash_password("admin123")

    connection.execute(
        "INSERT INTO admins VALUES (?, ?, ?, ?, ?)",
        (str(uuid4()), "admin", password_hash, password_salt, created_text),
    )

    products = [
        (
            "晨雾无火香氛",
            "HX-001",
            "家居香氛",
            16900,
            84,
            "上架",
            "🌿",
            "#dce8de",
            "雪松与白茶交织的柔和木质香，适合卧室与书房。",
        ),
        (
            "原木保温杯",
            "HX-002",
            "生活器物",
            12900,
            36,
            "上架",
            "🥛",
            "#eee2d1",
            "轻量杯身与原木杯盖，六小时保温，日常通勤随行。",
        ),
        (
            "云朵针织披肩",
            "HX-003",
            "服饰配件",
            23900,
            18,
            "上架",
            "🧣",
            "#eadde7",
            "细腻柔和的羊毛混纺披肩，适合春秋叠穿。",
        ),
        (
            "山茶护手霜礼盒",
            "HX-004",
            "个护礼盒",
            8900,
            126,
            "上架",
            "🎁",
            "#f3dfd2",
            "山茶籽油与乳木果配方，三支礼盒装。",
        ),
        (
            "轻羽托特包",
            "HX-005",
            "通勤包袋",
            31900,
            12,
            "上架",
            "👜",
            "#dde1ea",
            "轻量防泼水面料，内置电脑夹层，适合通勤。",
        ),
        (
            "春日花茶组合",
            "HX-006",
            "食品饮品",
            9900,
            56,
            "下架",
            "🍵",
            "#e1e9d8",
            "桂花、茉莉与雪梨片组合，清甜不腻。",
        ),
    ]
    product_ids: list[str] = []
    for index, product in enumerate(products):
        product_id = str(uuid4())
        product_ids.append(product_id)
        connection.execute(
            """
            INSERT INTO products (
                id, external_id, name, sku, category, price_cents, stock, status,
                emoji, accent, description, archived, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                product_id,
                f"demo-product-{index + 1}",
                *product,
                created_text,
                updated_text,
            ),
        )

    customers = [
        ("林予安", "13800132218", ["高复购", "香氛偏好"], "喜欢木质调，节日前可推荐礼盒。"),
        ("周南乔", "13622190432", ["新客"], "从视频内容进入店铺。"),
        ("顾清禾", "15988034216", ["高客单", "通勤"], "偏好简洁设计与实用包袋。"),
        ("沈知夏", "13755220981", ["礼赠"], "常购买礼盒，需要贺卡服务。"),
        ("陈屿", "18633092177", ["待跟进"], "咨询过花茶，等待补货通知。"),
    ]
    customer_ids: list[str] = []
    for index, (name, phone, tags, note) in enumerate(customers):
        customer_id = str(uuid4())
        customer_ids.append(customer_id)
        connection.execute(
            """
            INSERT INTO customers (
                id, external_id, name, phone, tags, note, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                f"demo-customer-{index + 1}",
                name,
                phone,
                "、".join(tags),
                note,
                "接口同步" if index in (0, 2) else "手工创建",
                created_text,
                updated_text,
            ),
        )

    order_specs = [
        (0, "待发货", [(0, 1), (3, 1)], "顺丰速运", "", "等待揽收", 2),
        (2, "已发货", [(3, 1), (1, 1)], "京东物流", "JDVA20261018001", "运输中", 5),
        (3, "已完成", [(2, 1)], "中通快递", "ZT20261012093", "已签收", 10),
        (1, "待付款", [(4, 1)], "", "", "暂无物流", 0),
        (4, "已取消", [(5, 1)], "", "", "已取消", 18),
        (0, "已完成", [(1, 1), (3, 2)], "顺丰速运", "SF20261002127", "已签收", 20),
    ]
    order_ids: list[str] = []
    order_amounts: list[int] = []
    for index, (customer_index, status, items, company, tracking, logistics, days_ago) in enumerate(
        order_specs
    ):
        order_id = str(uuid4())
        order_ids.append(order_id)
        order_created = (now - timedelta(days=days_ago)).isoformat()
        amount = sum(products[product_index][3] * quantity for product_index, quantity in items)
        order_amounts.append(amount)
        customer = customers[customer_index]
        order_no = f"HG202610{22 - index:02d}{index + 1:04d}"
        connection.execute(
            """
            INSERT INTO orders (
                id, external_id, order_no, customer_id, receiver, phone, address,
                status, total_cents, logistics_company, tracking_no, logistics_status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                f"demo-order-{index + 1}",
                order_no,
                customer_ids[customer_index],
                customer[0],
                customer[1],
                "浙江省杭州市西湖区文三路 88 号 3 幢 502",
                status,
                amount,
                company,
                tracking,
                logistics,
                order_created,
                order_created,
            ),
        )
        for product_index, quantity in items:
            product = products[product_index]
            connection.execute(
                """
                INSERT INTO order_items (
                    id, order_id, product_id, product_name, unit_price_cents, quantity, emoji
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    order_id,
                    product_ids[product_index],
                    product[0],
                    product[3],
                    quantity,
                    product[6],
                ),
            )

    conversation_specs = [
        (0, 0, "待人工", "物流一直没有更新", 2),
        (2, 1, "AI处理中", "通勤包还有现货吗？", 0),
        (3, 2, "AI处理中", "护手霜可以开发票吗？", 1),
        (4, None, "已结束", "花茶什么时候补货？", 0),
    ]
    conversation_ids: list[str] = []
    for index, (customer_index, order_index, status, subject, unread) in enumerate(
        conversation_specs
    ):
        conversation_id = str(uuid4())
        conversation_ids.append(conversation_id)
        last_message = (
            "您好，我理解您的着急，正在为您转接人工客服。"
            if index == 0
            else "您好，这款目前有现货，下午四点前下单可以当天发出。"
            if index == 1
            else "可以的，订单完成后支持申请电子发票。"
            if index == 2
            else "补货后我们会第一时间通知您。"
        )
        connection.execute(
            """
            INSERT INTO conversations (
                id, external_id, customer_id, order_id, status, subject,
                last_message, unread, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                f"demo-conversation-{index + 1}",
                customer_ids[customer_index],
                order_ids[order_index] if order_index is not None else None,
                status,
                subject,
                last_message,
                unread,
                updated_text,
            ),
        )
        message_sets = [
            [
                ("customer", "你好，我的快递三天没有更新了。"),
                ("ai", "抱歉让您久等了，我帮您查一下订单 HG202610220001 的物流。"),
                ("customer", "好的，有点着急，能不能帮我催一下？"),
                ("ai", "我已经记录您的诉求。由于涉及物流催件，正在为您转接人工客服。"),
            ],
            [
                ("customer", "轻羽托特包还有现货吗？"),
                ("ai", "您好，这款目前有现货，下午四点前下单可以当天发出。"),
            ],
            [
                ("customer", "护手霜礼盒可以开发票吗？"),
                ("ai", "可以的，订单完成后支持申请电子发票。"),
            ],
            [
                ("customer", "花茶什么时候补货？"),
                ("ai", "补货后我们会第一时间通知您。"),
            ],
        ][index]
        for message_index, (role, text) in enumerate(message_sets):
            connection.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    conversation_id,
                    role,
                    text,
                    (now - timedelta(minutes=(len(message_sets) - message_index) * 4)).isoformat(),
                ),
            )

    connection.execute(
        """
        INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            conversation_ids[0],
            order_ids[0],
            "物流补偿",
            3000,
            "物流超过 72 小时未更新，消费者情绪焦虑",
            "订单已揽收，最近一条物流记录停留在三天前",
            "pending",
            "",
            updated_text,
            updated_text,
        ),
    )
    connection.execute(
        """
        INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            conversation_ids[2],
            order_ids[2],
            "电子发票",
            0,
            "消费者申请开具电子发票",
            "订单已完成，可进入开票流程",
            "approved",
            "已确认抬头信息",
            (now - timedelta(days=1)).isoformat(),
            updated_text,
        ),
    )

    settings = {
        "shop_name": "禾光生活研究所",
        "shop_slogan": "把日常过得更有质感",
        "model_base_url": "https://api.example.com/v1",
        "model_name": "demo-model",
        "model_api_key": "",
        "sync_api_key": "demo_sync_key_12345678",
        "sync_last_at": updated_text,
    }
    connection.executemany(
        "INSERT INTO app_settings (key, value) VALUES (?, ?)",
        settings.items(),
    )
    connection.execute(
        "INSERT INTO sync_logs VALUES (?, ?, ?, ?)",
        (
            str(uuid4()),
            "/api/sync/v1/orders",
            "成功 8 条，跳过重复 2 条，失败 0 条",
            updated_text,
        ),
    )

