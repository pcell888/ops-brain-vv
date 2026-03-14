"""根据 .env 的 POSTGRES_URI 创建数据库（若不存在）。"""
import asyncio
import os
import sys

# 确保项目根在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urllib.parse import urlparse


def uri_to_conninfo(uri: str, dbname_override: str | None = None) -> str:
    parsed = urlparse(uri)
    if parsed.scheme not in ("postgresql", "postgres", "postgresql+asyncpg"):
        return uri
    parts = []
    if parsed.hostname:
        parts.append(f"host={parsed.hostname}")
    if parsed.port:
        parts.append(f"port={parsed.port}")
    db = dbname_override or (parsed.path.lstrip("/") if parsed.path and parsed.path != "/" else "postgres")
    parts.append(f"dbname={db}")
    if parsed.username:
        parts.append(f"user={parsed.username}")
    if parsed.password:
        parts.append(f"password={parsed.password}")
    return " ".join(parts)


async def main():
    from src.core.config import get_settings
    from psycopg import AsyncConnection

    settings = get_settings()
    parsed = urlparse(settings.postgres_uri)
    target_db = (parsed.path or "/").strip("/") or "postgres"
    conninfo_postgres = uri_to_conninfo(settings.postgres_uri, "postgres")
    async with await AsyncConnection.connect(conninfo_postgres, autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
            )
            if await cur.fetchone():
                print(f"数据库 {target_db!r} 已存在")
                return
            await cur.execute(f'CREATE DATABASE "{target_db}"')
            print(f"已创建数据库 {target_db!r}")


if __name__ == "__main__":
    asyncio.run(main())
