"""wlwq 服务配置 — 模拟业务库使用 PostgreSQL。"""

from __future__ import annotations

import os

# 模拟业务数据库：优先 WLWQ_POSTGRES_URI，否则 POSTGRES_URI，默认本地 wlwq
DEFAULT_WLWQ_POSTGRES_URI = "postgresql+asyncpg://postgres:postgres@localhost:5432/wlwq"


def get_wlwq_postgres_uri() -> str:
    return os.getenv("WLWQ_POSTGRES_URI") or os.getenv("POSTGRES_URI", DEFAULT_WLWQ_POSTGRES_URI)
