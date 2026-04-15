"""PostgreSQL URI → psycopg conninfo 转换（全局唯一实现）。"""

from __future__ import annotations

from urllib.parse import urlparse

from src.core.config import get_settings


def pg_uri_to_conninfo(uri: str, *, keepalives: bool = False) -> str:
    """将 postgresql:// 或 postgresql+asyncpg:// URL 转为 psycopg key=value conninfo。

    keepalives=True 时追加 TCP keepalive 参数（适用于长生命周期连接如 LangGraph checkpointer）。
    """
    uri = uri.strip()
    if len(uri) >= 2 and uri[0] == uri[-1] and uri[0] in ("'", '"'):
        uri = uri[1:-1].strip()
    parsed = urlparse(uri)
    if parsed.scheme not in ("postgresql", "postgres", "postgresql+asyncpg"):
        return uri
    parts: list[str] = []
    if parsed.hostname:
        parts.append(f"host={parsed.hostname}")
    if parsed.port:
        parts.append(f"port={parsed.port}")
    if parsed.path and parsed.path != "/":
        parts.append(f"dbname={parsed.path.lstrip('/')}")
    if parsed.username:
        parts.append(f"user={parsed.username}")
    if parsed.password:
        parts.append(f"password={parsed.password}")
    base = " ".join(parts)
    if not base:
        return uri
    if keepalives:
        return f"{base} keepalives=1 keepalives_idle=60 keepalives_interval=10 keepalives_count=3"
    return base


def get_conninfo(*, keepalives: bool = False) -> str:
    """基于当前 Settings 返回 conninfo（高频快捷方式）。"""
    return pg_uri_to_conninfo(get_settings().postgres_uri, keepalives=keepalives)
