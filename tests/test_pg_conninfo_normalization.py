from __future__ import annotations

from src.mcp_servers.tenant_router import _pg_uri_to_conninfo


def test_pg_uri_to_conninfo_handles_quoted_asyncpg_uri() -> None:
    raw = '"postgresql+asyncpg://postgres:postgres@localhost:5432/ops_brain_vv"'

    conninfo = _pg_uri_to_conninfo(raw)

    assert "host=localhost" in conninfo
    assert "port=5432" in conninfo
    assert "dbname=ops_brain_vv" in conninfo
    assert "user=postgres" in conninfo
    assert "password=postgres" in conninfo
