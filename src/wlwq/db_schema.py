"""wlwq PostgreSQL 表结构 — 对齐 wlwq-enterprise-service 业务库，支持 CMR/销售/任务效率/客户留存/人员系统。"""

from __future__ import annotations

import logging

from src.wlwq.database import get_pool

logger = logging.getLogger(__name__)

# ----- 消息与任务（原有） -----
MESSAGE_REMIND_SQL = """
CREATE TABLE IF NOT EXISTS message_remind (
  message_remind_id VARCHAR(20) PRIMARY KEY,
  account_id VARCHAR(20) DEFAULT '',
  model_status SMALLINT DEFAULT 0,
  message_title VARCHAR(1000) DEFAULT '',
  message_content TEXT,
  cover_image VARCHAR(1000) DEFAULT '',
  goods_name VARCHAR(1000) DEFAULT '',
  jump_type SMALLINT DEFAULT 0,
  model_id VARCHAR(64) DEFAULT '',
  read_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  del_status SMALLINT DEFAULT 0,
  message_type VARCHAR(64) DEFAULT ''
);
"""

AI_DIAGNOSIS_TASK_SQL = """
CREATE TABLE IF NOT EXISTS ai_diagnosis_task (
  task_id VARCHAR(32) PRIMARY KEY,
  tenant_id VARCHAR(32),
  store_id VARCHAR(32),
  plan_id VARCHAR(32),
  task_name VARCHAR(500),
  description TEXT,
  assignee_user_id INTEGER,
  assignee_account_id VARCHAR(32),
  assignee_dept_id VARCHAR(32),
  deadline VARCHAR(200),
  priority VARCHAR(20),
  status VARCHAR(20) DEFAULT 'pending',
  progress NUMERIC(5,2),
  remark TEXT,
  related_resources JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_ai_diagnosis_task_status_deadline
  ON ai_diagnosis_task (status, deadline) WHERE status NOT IN ('completed', 'cancelled');
"""

# ----- 统计/诊断用业务表（对齐业务库字段名与主键） -----
# 服务订单：任务效率、完成率
SERVICE_ORDER_SQL = """
CREATE TABLE IF NOT EXISTS service_order (
  service_order_id VARCHAR(20) PRIMARY KEY,
  order_sn VARCHAR(64),
  account_id VARCHAR(20),
  order_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  del_status SMALLINT DEFAULT 0
);
"""
# 商城订单：销售、客户留存、转化
STORE_ORDER_SQL = """
CREATE TABLE IF NOT EXISTS store_order (
  store_order_id VARCHAR(20) PRIMARY KEY,
  order_sn VARCHAR(32),
  account_id VARCHAR(20),
  user_id BIGINT,
  dept_id BIGINT,
  store_id VARCHAR(20),
  order_status SMALLINT DEFAULT 1,
  pay_time TIMESTAMP,
  delivery_time TIMESTAMP,
  complete_time TIMESTAMP,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  del_status SMALLINT DEFAULT 0,
  shipping_hours NUMERIC(10,2)
);
"""
# 用户优惠券：营销统计
ACCOUNT_COUPON_SQL = """
CREATE TABLE IF NOT EXISTS account_coupon (
  account_coupon_id VARCHAR(20) PRIMARY KEY,
  account_id VARCHAR(20),
  coupon_id VARCHAR(20),
  use_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  use_time TIMESTAMP
);
"""
# 经营数据：曝光/入店/下单（1曝光 2入店 3下单）
MANAGE_DATA_SQL = """
CREATE TABLE IF NOT EXISTS manage_data (
  manage_data_id BIGSERIAL PRIMARY KEY,
  exposure_location SMALLINT DEFAULT 1,
  account_id VARCHAR(20),
  date_type SMALLINT DEFAULT 1,
  day DATE DEFAULT CURRENT_DATE
);
"""
# 商城退款单
STORE_REFUND_ORDER_SQL = """
CREATE TABLE IF NOT EXISTS store_refund_order (
  store_refund_order_id VARCHAR(20) PRIMARY KEY,
  store_order_id VARCHAR(20),
  account_id VARCHAR(20),
  order_status SMALLINT,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
# 商城订单评价
STORE_ORDER_EVALUATE_SQL = """
CREATE TABLE IF NOT EXISTS store_order_evaluate (
  store_order_evaluate_id VARCHAR(20) PRIMARY KEY,
  store_order_id VARCHAR(20),
  store_id VARCHAR(20),
  account_id VARCHAR(20),
  star SMALLINT DEFAULT 0,
  level SMALLINT,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  del_status SMALLINT DEFAULT 0
);
"""
# 库存：库存诊断
STOCK_SQL = """
CREATE TABLE IF NOT EXISTS stock (
  stock_id VARCHAR(20) PRIMARY KEY,
  name VARCHAR(255),
  specification_model VARCHAR(255),
  stock_num INTEGER DEFAULT 0,
  user_id BIGINT,
  dept_id BIGINT,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  del_status SMALLINT DEFAULT 0
);
"""
# 商品
STORE_GOODS_SQL = """
CREATE TABLE IF NOT EXISTS store_goods (
  store_goods_id VARCHAR(20) PRIMARY KEY,
  store_id VARCHAR(20),
  dept_id BIGINT,
  goods_name VARCHAR(64),
  sale_status SMALLINT DEFAULT 0,
  del_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
STORE_ACTIVITIES_SQL = """
CREATE TABLE IF NOT EXISTS store_activities (
  id BIGSERIAL PRIMARY KEY,
  activity_name VARCHAR(128),
  activity_type SMALLINT DEFAULT 1,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  status SMALLINT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ----- 审批 -----
EXAMINE_INITIATE_SQL = """
CREATE TABLE IF NOT EXISTS examine_initiate (
  examine_initiate_id VARCHAR(20) PRIMARY KEY,
  store_id VARCHAR(32) DEFAULT '',
  title VARCHAR(500) DEFAULT '',
  content VARCHAR(500) DEFAULT '',
  biz_type VARCHAR(64) DEFAULT '',
  biz_id VARCHAR(64) DEFAULT '',
  user_id BIGINT,
  examine_status SMALLINT DEFAULT 1,
  response_hours NUMERIC(10,2),
  turnaround_hours NUMERIC(10,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

OA_EXAMINE_FLOW_SQL = """
CREATE TABLE IF NOT EXISTS oa_examine_flow (
  oa_examine_flow_id VARCHAR(20) PRIMARY KEY,
  examine_initiate_id VARCHAR(20),
  examine_tag VARCHAR(20) DEFAULT '0',
  user_id BIGINT,
  examine_sequence INT DEFAULT 1,
  examine_status SMALLINT DEFAULT 1,
  examine_remark VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ----- 优惠券 -----
COUPON_SQL = """
CREATE TABLE IF NOT EXISTS coupon (
  coupon_id VARCHAR(20) PRIMARY KEY,
  store_id VARCHAR(32) DEFAULT '',
  coupon_name VARCHAR(255) DEFAULT '',
  coupon_type SMALLINT DEFAULT 1,
  full_price NUMERIC(10,2) DEFAULT 0,
  reduce_price NUMERIC(10,2) DEFAULT 0,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ----- 秒杀 -----
SECKILL_APPLY_SQL = """
CREATE TABLE IF NOT EXISTS seckill_apply (
  seckill_apply_id VARCHAR(20) PRIMARY KEY,
  store_id VARCHAR(32) DEFAULT '',
  title VARCHAR(255) DEFAULT '',
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  status SMALLINT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
SECKILL_GOODS_TIME_SQL = """
CREATE TABLE IF NOT EXISTS seckill_goods_time (
  seckill_goods_time_id VARCHAR(20) PRIMARY KEY,
  store_goods_id VARCHAR(20),
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  del_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  discount NUMERIC(10,2),
  limit_num INT DEFAULT 0,
  goods_num INT DEFAULT 0,
  surplus_goods_num INT DEFAULT 0,
  seckill_apply_id VARCHAR(20)
);
"""

# ----- CRM 客户 -----
CLIENT_RECORD_SQL = """
CREATE TABLE IF NOT EXISTS client_record (
  client_record_id VARCHAR(20) PRIMARY KEY,
  client_name VARCHAR(64),
  contact_person VARCHAR(255),
  contact_number VARCHAR(255),
  payment_amount NUMERIC(20,2) DEFAULT 0,
  paid_amount NUMERIC(20,2) DEFAULT 0,
  province VARCHAR(30),
  city VARCHAR(30),
  county VARCHAR(30),
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  del_status SMALLINT DEFAULT 0
);
"""

# ----- 销售（销售合同、销售单） -----
SALES_CONTRACT_SQL = """
CREATE TABLE IF NOT EXISTS sales_contract (
  sales_contract_id VARCHAR(20) PRIMARY KEY,
  contract_number VARCHAR(20),
  client_record_id VARCHAR(20),
  client_name VARCHAR(64),
  sign_time TIMESTAMP,
  expire_time TIMESTAMP,
  money_total NUMERIC(20,2) DEFAULT 0,
  paid_money_total NUMERIC(20,2) DEFAULT 0,
  unpaid_money_total NUMERIC(20,2) DEFAULT 0,
  user_id BIGINT,
  dept_id BIGINT,
  dept_name VARCHAR(255),
  examine_status SMALLINT DEFAULT 0,
  del_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SALES_SQL = """
CREATE TABLE IF NOT EXISTS sales (
  sales_id VARCHAR(20) PRIMARY KEY,
  sales_contract_id VARCHAR(20),
  client_record_id VARCHAR(20),
  client_name VARCHAR(64),
  money_total NUMERIC(20,2) DEFAULT 0,
  sign_time TIMESTAMP,
  contract_number VARCHAR(20),
  user_id BIGINT,
  dept_id BIGINT,
  dept_name VARCHAR(255),
  examine_status SMALLINT DEFAULT 0,
  outbound_status SMALLINT DEFAULT 0,
  del_status SMALLINT DEFAULT 0,
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ----- 人员系统（配发任务） -----
SYS_DEPT_SQL = """
CREATE TABLE IF NOT EXISTS sys_dept (
  dept_id BIGSERIAL PRIMARY KEY,
  parent_id BIGINT DEFAULT 0,
  ancestors VARCHAR(50) DEFAULT '',
  dept_name VARCHAR(30) DEFAULT '',
  order_num INT DEFAULT 0,
  leader VARCHAR(20),
  phone VARCHAR(11),
  status CHAR(1) DEFAULT '0',
  del_flag CHAR(1) DEFAULT '0',
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SYS_USER_SQL = """
CREATE TABLE IF NOT EXISTS sys_user (
  user_id BIGSERIAL PRIMARY KEY,
  dept_id BIGINT,
  user_name VARCHAR(30) NOT NULL,
  nick_name VARCHAR(30) NOT NULL,
  user_type SMALLINT DEFAULT 0,
  phonenumber VARCHAR(11) DEFAULT '',
  status CHAR(1) DEFAULT '0',
  del_flag CHAR(1) DEFAULT '0',
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SYS_POST_SQL = """
CREATE TABLE IF NOT EXISTS sys_post (
  post_id BIGSERIAL PRIMARY KEY,
  post_code VARCHAR(64),
  post_name VARCHAR(50) NOT NULL,
  post_sort INT DEFAULT 0,
  status CHAR(1) DEFAULT '0',
  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SYS_USER_POST_SQL = """
CREATE TABLE IF NOT EXISTS sys_user_post (
  user_id BIGINT NOT NULL,
  post_id BIGINT NOT NULL,
  PRIMARY KEY (user_id, post_id)
);
"""


# 旧版统计表（id SERIAL 主键），迁移时需先删后建
_OLD_STATS_TABLES = [
    "store_order_evaluate",
    "store_refund_order",
    "store_order",
    "service_order",
    "account_coupon",
    "manage_data",
    "stock",
    "store_goods",
    "store_activities",
]


async def _migrate_wlwq_old_schema(conn) -> bool:
    """若存在旧表结构（如 service_order.id），则删除旧表以便用业务库结构重建。返回是否执行过迁移。"""
    try:
        row = await conn.fetchrow(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'service_order' AND column_name = 'id'"
        )
        if not row:
            return False
        # 旧结构存在（主键为 id），执行迁移
        for table in _OLD_STATS_TABLES:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info("wlwq migration: dropped old table %s", table)
            except Exception as e:
                logger.warning("wlwq migration drop %s: %s", table, e)
        return True
    except Exception as e:
        logger.warning("wlwq migration check: %s", e)
        return False


async def ensure_wlwq_tables():
    """创建/更新表结构；若检测到旧表则先迁移再建表。"""
    pool = await get_pool()
    stmts = [
        ("message_remind", MESSAGE_REMIND_SQL.strip()),
        ("ai_diagnosis_task", AI_DIAGNOSIS_TASK_SQL.strip()),
        ("service_order", SERVICE_ORDER_SQL.strip()),
        ("store_order", STORE_ORDER_SQL.strip()),
        ("account_coupon", ACCOUNT_COUPON_SQL.strip()),
        ("manage_data", MANAGE_DATA_SQL.strip()),
        ("store_refund_order", STORE_REFUND_ORDER_SQL.strip()),
        ("store_order_evaluate", STORE_ORDER_EVALUATE_SQL.strip()),
        ("stock", STOCK_SQL.strip()),
        ("store_goods", STORE_GOODS_SQL.strip()),
        ("store_activities", STORE_ACTIVITIES_SQL.strip()),
        ("examine_initiate", EXAMINE_INITIATE_SQL.strip()),
        ("oa_examine_flow", OA_EXAMINE_FLOW_SQL.strip()),
        ("coupon", COUPON_SQL.strip()),
        ("seckill_apply", SECKILL_APPLY_SQL.strip()),
        ("seckill_goods_time", SECKILL_GOODS_TIME_SQL.strip()),
        ("client_record", CLIENT_RECORD_SQL.strip()),
        ("sales_contract", SALES_CONTRACT_SQL.strip()),
        ("sales", SALES_SQL.strip()),
        ("sys_dept", SYS_DEPT_SQL.strip()),
        ("sys_user", SYS_USER_SQL.strip()),
        ("sys_post", SYS_POST_SQL.strip()),
        ("sys_user_post", SYS_USER_POST_SQL.strip()),
    ]
    async with pool.acquire() as conn:
        await _migrate_wlwq_old_schema(conn)
        for name, sql in stmts:
            try:
                for stmt in (s.strip() for s in sql.split(";") if s.strip()):
                    await conn.execute(stmt)
                logger.info("wlwq table %s ensured", name)
            except Exception as e:
                logger.warning("wlwq ensure table %s: %s", name, e)
        for table, col in [("message_remind", "model_id")]:
            try:
                await conn.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE VARCHAR(64)")
            except Exception:
                pass
        try:
            await conn.execute(
                "ALTER TABLE ai_diagnosis_task ALTER COLUMN deadline TYPE VARCHAR(200) USING (deadline::text)"
            )
        except Exception:
            pass
        await _seed_business_data_if_empty(conn)


async def _seed_business_data_if_empty(conn):
    """业务表为空时插入模拟数据（CRM/销售/任务效率/客户留存/人员）。"""
    n = await conn.fetchval("SELECT COUNT(*) FROM service_order")
    if n and int(n) > 0:
        return

    # 人员：部门树 + 用户
    await conn.execute(
        "INSERT INTO sys_dept (dept_id, parent_id, dept_name, order_num) VALUES (1, 0, '总公司', 0) ON CONFLICT (dept_id) DO NOTHING"
    )
    for did, pid, name, ord in [(2, 1, "销售部", 1), (3, 1, "运营部", 2), (4, 1, "客服部", 3)]:
        await conn.execute(
            "INSERT INTO sys_dept (dept_id, parent_id, dept_name, order_num) VALUES ($1, $2, $3, $4) ON CONFLICT (dept_id) DO NOTHING",
            did, pid, name, ord,
        )
    try:
        await conn.execute("SELECT setval(pg_get_serial_sequence('sys_dept', 'dept_id'), 4)")
    except Exception:
        pass
    for uid, dept_id, uname, nick in [(1, 2, "admin", "管理员"), (2, 2, "sales1", "销售主管"), (3, 3, "ops1", "运营经理"), (4, 4, "cs1", "客服主管")]:
        await conn.execute(
            "INSERT INTO sys_user (user_id, dept_id, user_name, nick_name) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING",
            uid, dept_id, uname, nick,
        )
    try:
        await conn.execute("SELECT setval(pg_get_serial_sequence('sys_user', 'user_id'), 4)")
    except Exception:
        pass
    await conn.execute(
        "INSERT INTO sys_post (post_id, post_name, post_sort) VALUES (1, '销售经理', 1), (2, '运营专员', 2) ON CONFLICT (post_id) DO NOTHING"
    )
    await conn.executemany(
        "INSERT INTO sys_user_post (user_id, post_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        [(2, 1), (3, 2)],
    )

    # 客户（CRM）
    for i in range(1, 51):
        await conn.execute(
            "INSERT INTO client_record (client_record_id, client_name, contact_person, contact_number, paid_amount, payment_amount, province, city) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (client_record_id) DO NOTHING",
            f"cr_{i:04d}", f"客户{i}", f"联系人{i}", f"1380000{i:04d}", 10000 + i * 500, 2000 + i * 100, "广东省", "深圳市",
        )

    # 销售合同 + 销售单
    for i in range(1, 21):
        cid, sid = f"sc_{i:04d}", f"sl_{i:04d}"
        await conn.execute(
            "INSERT INTO sales_contract (sales_contract_id, contract_number, client_record_id, client_name, sign_time, money_total, paid_money_total, user_id, dept_id, dept_name, examine_status) "
            "VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP - ($5 || ' days')::interval, $6, $7, 2, 2, '销售部', 3) ON CONFLICT (sales_contract_id) DO NOTHING",
            cid, f"HT{i:05d}", f"cr_{i:04d}", f"客户{i}", str(30 + i), 50000 + i * 5000, 30000 + i * 2000,
        )
        await conn.execute(
            "INSERT INTO sales (sales_id, sales_contract_id, client_record_id, client_name, money_total, sign_time, contract_number, user_id, dept_id, dept_name, examine_status, outbound_status) "
            "VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, $6, 2, 2, '销售部', 3, 1) ON CONFLICT (sales_id) DO NOTHING",
            sid, cid, f"cr_{i:04d}", f"客户{i}", 50000 + i * 5000, f"HT{i:05d}",
        )

    # 服务订单：100 单，85 完成 (order_status=8)
    for i in range(1, 101):
        status = 8 if i <= 85 else 0
        await conn.execute(
            "INSERT INTO service_order (service_order_id, order_sn, order_status) VALUES ($1, $2, $3) ON CONFLICT (service_order_id) DO NOTHING",
            f"so_{i:05d}", f"SN{i:06d}", status,
        )

    # 商城订单：2280 单，2050 完成，820 用户，发货时长约 12h
    for i in range(1, 2281):
        uid = (i - 1) % 820
        status = 6 if i <= 2050 else 1
        await conn.execute(
            "INSERT INTO store_order (store_order_id, order_sn, account_id, order_status, shipping_hours) VALUES ($1, $2, $3, $4, 12.0) ON CONFLICT (store_order_id) DO NOTHING",
            f"ord_{i:06d}", f"MO{i:07d}", f"u{uid}", status,
        )

    # 优惠券：5000 张，1850 已用
    for i in range(1, 5001):
        use_status = 1 if i <= 1850 else 0
        await conn.execute(
            "INSERT INTO account_coupon (account_coupon_id, account_id, use_status) VALUES ($1, $2, $3) ON CONFLICT (account_coupon_id) DO NOTHING",
            f"ac_{i:06d}", f"u{i % 1000}", use_status,
        )

    # 经营数据：曝光 12600 条（date_type=1）
    await conn.executemany(
        "INSERT INTO manage_data (account_id, date_type) VALUES ($1, 1)",
        [(f"u{i % 2000}",) for i in range(12600)],
    )

    # 退款单 82 笔（store_order_id 与 store_order 一致 6 位）
    for i in range(1, 83):
        await conn.execute(
            "INSERT INTO store_refund_order (store_refund_order_id, store_order_id) VALUES ($1, $2) ON CONFLICT (store_refund_order_id) DO NOTHING",
            f"ro_{i:05d}", f"ord_{i:06d}",
        )

    # 评价 1680 条，1462 条 4 星及以上
    stars = [5] * 1200 + [4] * 262 + [3] * 150 + [2] * 50 + [1] * 18
    for i, star in enumerate(stars, 1):
        await conn.execute(
            "INSERT INTO store_order_evaluate (store_order_evaluate_id, store_order_id, star) VALUES ($1, $2, $3) ON CONFLICT (store_order_evaluate_id) DO NOTHING",
            f"ev_{i:05d}", f"ord_{i:06d}", star,
        )

    # 库存：12 缺货、35 积压、其余正常
    for i in range(1, 13):
        await conn.execute(
            "INSERT INTO stock (stock_id, name, stock_num, user_id, dept_id) VALUES ($1, $2, 0, 1, 2) ON CONFLICT (stock_id) DO NOTHING",
            f"sk_{i:04d}", f"商品{i}",
        )
    for i in range(13, 48):
        await conn.execute(
            "INSERT INTO stock (stock_id, name, stock_num, user_id, dept_id) VALUES ($1, $2, 600, 1, 2) ON CONFLICT (stock_id) DO NOTHING",
            f"sk_{i:04d}", f"商品{i}",
        )
    for i in range(48, 248):
        await conn.execute(
            "INSERT INTO stock (stock_id, name, stock_num, user_id, dept_id) VALUES ($1, $2, $3, 1, 2) ON CONFLICT (stock_id) DO NOTHING",
            f"sk_{i:04d}", f"商品{i}", 100 + (i % 400),
        )

    # 商品 480
    for i in range(1, 481):
        await conn.execute(
            "INSERT INTO store_goods (store_goods_id, store_id, goods_name, sale_status) VALUES ($1, 'st_001', $2, 1) ON CONFLICT (store_goods_id) DO NOTHING",
            f"sg_{i:05d}", f"SKU商品{i}",
        )

    await conn.execute(
        "INSERT INTO store_activities (activity_name, activity_type, status) VALUES ('年度大促', 1, 1)"
    )

    for i in range(1, 11):
        await conn.execute(
            "INSERT INTO seckill_goods_time (seckill_goods_time_id, store_goods_id, goods_num, surplus_goods_num, seckill_apply_id) "
            "VALUES ($1, $2, $3, $4, 'sa_001') ON CONFLICT (seckill_goods_time_id) DO NOTHING",
            f"sgt_{i:04d}", f"sg_{i:05d}", 50, max(50 - i * 9, 5),
        )

    logger.info("wlwq business seed data inserted")
