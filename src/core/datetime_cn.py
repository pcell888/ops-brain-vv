"""API 出参：绝对时刻统一序列化为 Asia/Shanghai 的 ISO 8601（秒精度）。

与诊断列表 `_list_item_cn_time` 约定一致：数据库 naive datetime 按 UTC 理解
（PostgreSQL timestamptz 经驱动常见形态），再换算为北京时间，避免前端按「本地字面」误解析。
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from src.core.config import CN_TZ


def to_utc_aware(dt: datetime) -> datetime:
    """将 datetime 归一为 UTC aware，便于与 timedelta 运算。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def serialize_instant_cn(value: Any) -> str | None:
    """将时刻转为北京时间 ISO 字符串；无法解析的字符串原样返回；其余返回 None。"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date) and not isinstance(value, datetime):
        dt = datetime.combine(value, time.min, tzinfo=CN_TZ)
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        s = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return value.strip() if isinstance(value, str) else None
    else:
        return None

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CN_TZ).replace(microsecond=0).isoformat(timespec="seconds")
    return None
