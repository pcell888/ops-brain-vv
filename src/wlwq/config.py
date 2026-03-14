"""wlwq 服务配置 — MySQL 连接等。"""

from __future__ import annotations

import os


def get_mysql_config() -> dict:
    return {
        "host": os.getenv("WLWQ_MYSQL_HOST", "192.168.1.249"),
        "port": int(os.getenv("WLWQ_MYSQL_PORT", "3306")),
        "user": os.getenv("WLWQ_MYSQL_USER", "wlwq"),
        "password": os.getenv("WLWQ_MYSQL_PASSWORD", "Mysql@db$123!"),
        "db": os.getenv("WLWQ_MYSQL_DATABASE", "wlwq-enterprise-service"),
        "autocommit": True,
    }
