import io
import time
import json
import random
import psycopg2
import yaml
from datetime import datetime, timedelta
from typing import Iterable, List, Tuple, Dict, Any
from psycopg2 import sql

# ========= 固定随机种子，保证可复现 =========
random.seed(42)

# ========= DDL（含完整中文注释）=========
DDL = r"""
CREATE SCHEMA IF NOT EXISTS {schema};
SET search_path TO {schema};

-- 品类表
CREATE TABLE IF NOT EXISTS categories (
  category_id   INT PRIMARY KEY,
  category_name TEXT NOT NULL
);
COMMENT ON TABLE  categories IS '商品品类维表';
COMMENT ON COLUMN categories.category_id   IS '品类ID（主键）';
COMMENT ON COLUMN categories.category_name IS '品类名称';

-- 用户表
CREATE TABLE IF NOT EXISTS users (
  user_id    INT PRIMARY KEY,
  full_name  TEXT,
  email      TEXT UNIQUE,
  created_at TIMESTAMP NOT NULL
);
COMMENT ON TABLE  users IS '用户主数据';
COMMENT ON COLUMN users.user_id    IS '用户ID（主键）';
COMMENT ON COLUMN users.full_name  IS '用户姓名';
COMMENT ON COLUMN users.email      IS '邮箱（唯一）';
COMMENT ON COLUMN users.created_at IS '创建时间';

-- 商品表
CREATE TABLE IF NOT EXISTS products (
  product_id      INT PRIMARY KEY,
  sku             TEXT UNIQUE,
  product_name    TEXT NOT NULL,
  category_id     INT REFERENCES categories(category_id),
  base_price      NUMERIC(12,2) NOT NULL,
  currency        TEXT NOT NULL,
  attributes_json JSONB
);
COMMENT ON TABLE  products IS '商品主数据';
COMMENT ON COLUMN products.product_id      IS '商品ID（主键）';
COMMENT ON COLUMN products.sku             IS 'SKU（唯一）';
COMMENT ON COLUMN products.product_name    IS '商品名称';
COMMENT ON COLUMN products.category_id     IS '所属品类ID';
COMMENT ON COLUMN products.base_price      IS '基础单价（USD）';
COMMENT ON COLUMN products.currency        IS '币种';
COMMENT ON COLUMN products.attributes_json IS '属性JSON（brand/color/tags等）';

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
  order_id      INT PRIMARY KEY,
  user_id       INT REFERENCES users(user_id),
  order_ts      TIMESTAMP NOT NULL,
  sales_channel TEXT CHECK (sales_channel IN ('web','mobile','store')),
  status        TEXT CHECK (status IN ('created','paid','shipped','delivered','cancelled')),
  notes         JSONB
);
COMMENT ON TABLE  orders IS '订单主表';
COMMENT ON COLUMN orders.order_id      IS '订单ID（主键）';
COMMENT ON COLUMN orders.user_id       IS '下单用户ID';
COMMENT ON COLUMN orders.order_ts      IS '下单时间';
COMMENT ON COLUMN orders.sales_channel IS '销售渠道：web/mobile/store';
COMMENT ON COLUMN orders.status        IS '订单状态';
COMMENT ON COLUMN orders.notes         IS '备注JSON';

-- 订单明细
CREATE TABLE IF NOT EXISTS order_items (
  order_id   INT REFERENCES orders(order_id),
  item_no    INT,
  product_id INT REFERENCES products(product_id),
  qty        INT,
  unit_price NUMERIC(12,2),
  line_total NUMERIC(12,2),
  PRIMARY KEY (order_id, item_no)
);
COMMENT ON TABLE  order_items IS '订单明细';
COMMENT ON COLUMN order_items.order_id   IS '订单ID（外键）';
COMMENT ON COLUMN order_items.item_no    IS '行号（主键的一部分）';
COMMENT ON COLUMN order_items.product_id IS '商品ID';
COMMENT ON COLUMN order_items.qty        IS '数量';
COMMENT ON COLUMN order_items.unit_price IS '成交单价';
COMMENT ON COLUMN order_items.line_total IS '行金额';

-- 行为事件
CREATE TABLE IF NOT EXISTS events (
  event_id        INT PRIMARY KEY,
  user_id         INT REFERENCES users(user_id),
  event_type      TEXT,
  event_ts        TIMESTAMP,
  properties_json JSONB
);
COMMENT ON TABLE  events IS '行为事件表（埋点/AB 实验）';
COMMENT ON COLUMN events.event_id        IS '事件ID（主键）';
COMMENT ON COLUMN events.user_id         IS '用户ID';
COMMENT ON COLUMN events.event_type      IS '事件类型：page_view/search/add_to_cart/checkout/purchase/login';
COMMENT ON COLUMN events.event_ts        IS '事件时间';
COMMENT ON COLUMN events.properties_json IS '事件属性JSON（device/ab_bucket/url/ref等）';
"""

# ========= 维度值 =========
CATEGORIES = ["Laptop", "Phone", "Tablet", "Audio", "Toy", "Clothing", "Sports", "Book", "Furniture", "Food"]
BRANDS = ["Acme", "Zenith", "Nova", "Apex", "Pioneer", "Artemis"]
COLORS = ["red", "blue", "black", "white", "gray", "green"]
EVENT_TYPES = ["page_view", "search", "add_to_cart", "checkout", "purchase", "login"]
CHANNELS = ["web", "mobile", "store"]
STATUSES = ["created", "paid", "shipped", "delivered", "cancelled"]
DEVICES = ["ios", "android", "desktop"]
AB_BUCKETS = ["A", "B"]
URLS = ["/home", "/product", "/category", "/cart", "/checkout", "/profile"]
REFS = ["direct", "ad", "email", "social", "search"]


# ========= 小工具 =========
def rand_dt(days_back: int) -> datetime:
    """生成过去 days_back 天内的随机时间（含随机秒）"""
    return datetime.now() - timedelta(days=random.randint(0, days_back),
                                      seconds=random.randint(0, 24 * 3600 - 1))


def csv_escape(val) -> str:
    """CSV 简易转义（与 COPY CSV HEADER 配合使用）"""
    if val is None:
        return ""
    s = str(val)
    if any(ch in s for ch in [',', '"', '\n', '\r']):
        return '"' + s.replace('"', '""') + '"'
    return s


def copy_from_rows(cur, schema: str, table: str, columns: List[str],
                   rows: Iterable[Tuple], batch_size: int) -> int:
    """
    使用内存流批量 COPY，每 batch_size 行写入一次。
    rows 是生成器或可迭代对象（边生边导，内存友好）。
    返回总写入行数。
    """
    cols = ",".join(columns)
    header = ",".join(columns) + "\n"
    buf = io.StringIO()
    count = 0
    total = 0

    for row in rows:
        if count == 0:
            buf.write(header)
        buf.write(",".join(csv_escape(x) for x in row) + "\n")
        count += 1
        total += 1

        if count >= batch_size:
            buf.seek(0)
            cur.copy_expert(f"COPY {schema}.{table} ({cols}) FROM STDIN WITH CSV HEADER", buf)
            buf.close()
            buf = io.StringIO()
            count = 0

    if count > 0:
        buf.seek(0)
        cur.copy_expert(f"COPY {schema}.{table} ({cols}) FROM STDIN WITH CSV HEADER", buf)
        buf.close()

    return total


# ========= 数据生成器（生成器函数，流式）=========
def gen_categories() -> Iterable[Tuple[int, str]]:
    for i, c in enumerate(CATEGORIES, start=1):
        yield (i, c)


def gen_users(n_users: int) -> Iterable[Tuple[int, str, str, str]]:
    for i in range(1, n_users + 1):
        yield (i, f"User_{i}", f"user{i}@demo.com", rand_dt(730).isoformat(sep=' '))


def gen_products(n_products: int) -> Iterable[Tuple[int, str, str, int, str, str, str]]:
    for i in range(1, n_products + 1):
        cat = random.randint(1, len(CATEGORIES))
        attr = {
            "brand": random.choice(BRANDS),
            "color": random.choice(COLORS),
            "tags": random.sample(["eco", "premium", "budget", "new", "refurbished", "limited"], k=random.randint(1, 3))
        }
        price = round(random.uniform(5, 3000), 2)
        yield (i, f"SKU-{i:06d}", f"Product_{i}", cat, f"{price:.2f}", "USD",
               json.dumps(attr, ensure_ascii=False))


def gen_orders_and_items(n_orders: int, n_users: int, n_products: int):
    """返回两个独立的生成器：orders_rows_iter, items_rows_iter"""

    def orders_iter():
        for oid in range(1, n_orders + 1):
            uid = random.randint(1, n_users)
            ts = rand_dt(730).isoformat(sep=' ')
            channel = random.choice(CHANNELS)
            status = random.choice(STATUSES)
            notes = json.dumps({"note": "demo", "gift": random.random() < 0.05}, ensure_ascii=False)
            yield (oid, uid, ts, channel, status, notes)

    def items_iter():
        for oid in range(1, n_orders + 1):
            for item_no in range(1, random.randint(2, 5)):
                pid = random.randint(1, n_products)
                qty = random.randint(1, 3)
                price = round(random.uniform(5, 3000), 2)
                line_total = round(qty * price, 2)
                yield (oid, item_no, pid, qty, f"{price:.2f}", f"{line_total:.2f}")

    return orders_iter(), items_iter()


def gen_events(n_events: int, n_users: int) -> Iterable[Tuple[int, int, str, str, str]]:
    for eid in range(1, n_events + 1):
        uid = random.randint(1, n_users)
        etype = random.choice(EVENT_TYPES)
        ts = rand_dt(365).isoformat(sep=' ')
        props = {
            "device": random.choice(DEVICES),
            "ab_bucket": random.choice(AB_BUCKETS),
            "url": random.choice(URLS),
            "ref": random.choice(REFS),
            "ip": f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
        }
        yield (eid, uid, etype, ts, json.dumps(props, ensure_ascii=False))


# ========= 数据库保障：缺库即建 =========
def ensure_database(dbconf: Dict[str, Any]) -> None:
    """
    若目标数据库不存在，则连接到 admin_db(默认 postgres) 创建之。
    需要角色具备 CREATEDB 或超级用户权限。
    """
    admin_db = dbconf.get("admin_db", "postgres")
    conn = psycopg2.connect(
        dbname=admin_db,
        user=dbconf["user"],
        password=dbconf["password"],
        host=dbconf["host"],
        port=dbconf["port"],
    )
    conn.autocommit = True  # CREATE DATABASE 不能在事务里
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbconf["dbname"],))
    exists = cur.fetchone()
    if not exists:
        owner = dbconf.get("owner", dbconf["user"])
        encoding = dbconf.get("encoding", "UTF8")
        cur.execute(
            sql.SQL("CREATE DATABASE {} OWNER {} ENCODING %s TEMPLATE template0")
            .format(sql.Identifier(dbconf["dbname"]), sql.Identifier(owner)),
            (encoding,),
        )
        print(f"🆕 Created database {dbconf['dbname']} (owner={owner}, encoding={encoding})")
    cur.close()
    conn.close()


# ========= 主流程 =========
def main():
    # 读取配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db = cfg["db"]
    data = cfg["data"]
    mode = cfg.get("mode", {})
    batch = cfg.get("batch", {})
    perf = cfg.get("perf", {})

    schema = mode.get("schema", "retail")
    truncate = bool(mode.get("truncate", True))

    # 确保数据库存在
    ensure_database(db)

    # 连接目标数据库
    conn = psycopg2.connect(
        dbname=db["dbname"],
        user=db["user"],
        password=db["password"],
        host=db["host"],
        port=db["port"]
    )
    conn.autocommit = False
    cur = conn.cursor()

    # 性能参数（会话级）
    def set_perf():
        if "synchronous_commit" in perf:
            cur.execute(f"SET LOCAL synchronous_commit = {perf['synchronous_commit']};")
        if "work_mem_mb" in perf:
            cur.execute(f"SET LOCAL work_mem = '{int(perf['work_mem_mb'])}MB';")
        if "maintenance_work_mem_mb" in perf:
            cur.execute(f"SET LOCAL maintenance_work_mem = '{int(perf['maintenance_work_mem_mb'])}MB';")

    start_all = time.time()
    try:
        print("⚙️ Creating schema & tables ...")
        cur.execute(DDL.format(schema=schema))
        conn.commit()

        if truncate:
            print("🧹 Truncating old data ...")
            cur.execute(
                f"TRUNCATE {schema}.order_items, {schema}.orders, {schema}.events, "
                f"{schema}.products, {schema}.users, {schema}.categories RESTART IDENTITY CASCADE;"
            )
            conn.commit()

        set_perf()

        # categories
        t0 = time.time()
        print("➡️  Loading categories ...")
        total = copy_from_rows(
            cur, schema, "categories",
            ["category_id", "category_name"],
            gen_categories(),
            batch_size=int(batch.get("categories", 10000))
        )
        conn.commit()
        print(f"   done: {total} rows in {time.time() - t0:.2f}s")

        # users
        t0 = time.time()
        print("➡️  Loading users ...")
        total = copy_from_rows(
            cur, schema, "users",
            ["user_id", "full_name", "email", "created_at"],
            gen_users(int(data["users"])),
            batch_size=int(batch.get("users", 50000))
        )
        conn.commit()
        print(f"   done: {total} rows in {time.time() - t0:.2f}s")

        # products
        t0 = time.time()
        print("➡️  Loading products ...")
        total = copy_from_rows(
            cur, schema, "products",
            ["product_id", "sku", "product_name", "category_id", "base_price", "currency", "attributes_json"],
            gen_products(int(data["products"])),
            batch_size=int(batch.get("products", 50000))
        )
        conn.commit()
        print(f"   done: {total} rows in {time.time() - t0:.2f}s")

        # orders + order_items
        print("➡️  Loading orders & order_items ...")
        orders_rows, items_rows = gen_orders_and_items(
            int(data["orders"]),
            int(data["users"]),
            int(data["products"])
        )

        t0 = time.time()
        total_o = copy_from_rows(
            cur, schema, "orders",
            ["order_id", "user_id", "order_ts", "sales_channel", "status", "notes"],
            orders_rows,
            batch_size=int(batch.get("orders", 20000))
        )
        conn.commit()
        print(f"   orders: {total_o} rows in {time.time() - t0:.2f}s")

        t0 = time.time()
        total_i = copy_from_rows(
            cur, schema, "order_items",
            ["order_id", "item_no", "product_id", "qty", "unit_price", "line_total"],
            items_rows,
            batch_size=int(batch.get("orders", 20000))
        )
        conn.commit()
        print(f"   items : {total_i} rows in {time.time() - t0:.2f}s")

        # events
        t0 = time.time()
        print("➡️  Loading events ...")
        total = copy_from_rows(
            cur, schema, "events",
            ["event_id", "user_id", "event_type", "event_ts", "properties_json"],
            gen_events(int(data["events"]), int(data["users"])),
            batch_size=int(batch.get("events", 100000))
        )
        conn.commit()
        print(f"   done: {total} rows in {time.time() - t0:.2f}s")

        # row counts
        print("\n📊 Row counts:")
        for t in ["categories", "users", "products", "orders", "order_items", "events"]:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}")
                        .format(sql.Identifier(schema), sql.Identifier(t)))
            print(f"  - {t:<12} : {cur.fetchone()[0]}")

        print(f"\n✅ All done in {time.time() - start_all:.2f}s")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
