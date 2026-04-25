"""诊断会话状态仓储 — diag_sessions 表，替代 LangGraph checkpoint。"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from psycopg.rows import dict_row

from src.core.db_pool import get_conn
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def create_session(
    thread_id: str,
    tenant_id: str,
    store_id: str = "",
    trigger_type: str = "manual",
    triggered_by: str | None = None,
    selected_dimensions: list[str] | None = None,
    selected_indicators: list[str] | None = None,
    auth_token: str | None = None,
    phase: str = "collecting",
    state_json: dict | None = None,
) -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO diag_sessions
                        (thread_id, tenant_id, store_id, phase, state_json,
                         trigger_type, triggered_by, selected_dimensions, selected_indicators, auth_token)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (thread_id) DO UPDATE SET
                        phase = EXCLUDED.phase,
                        state_json = EXCLUDED.state_json,
                        updated_at = NOW()
                    """,
                    (
                        thread_id[:128],
                        tenant_id[:32],
                        store_id[:32],
                        phase[:32],
                        json.dumps(state_json or {}, ensure_ascii=False),
                        trigger_type[:32],
                        (triggered_by or "")[:128] if triggered_by else None,
                        json.dumps(selected_dimensions) if selected_dimensions else None,
                        json.dumps(selected_indicators) if selected_indicators else None,
                        auth_token,
                    ),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("创建诊断会话失败", thread_id=thread_id) from e


async def get_session(thread_id: str) -> dict | None:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT thread_id, tenant_id, store_id, phase, state_json,
                           trigger_type, triggered_by, selected_dimensions, selected_indicators,
                           auth_token, created_at, updated_at
                    FROM diag_sessions
                    WHERE thread_id = %s
                    """,
                    (thread_id[:128],),
                )
                return await cur.fetchone()
    except Exception as e:
        raise AppError("查询诊断会话失败", thread_id=thread_id) from e


async def get_session_phase(thread_id: str) -> str | None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT phase FROM diag_sessions WHERE thread_id = %s",
                    (thread_id[:128],),
                )
                row = await cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        raise AppError("查询诊断会话阶段失败", thread_id=thread_id) from e


async def update_session_phase(
    thread_id: str,
    phase: str,
    state_updates: dict | None = None,
) -> None:
    if state_updates:
        state_json = json.dumps(state_updates, ensure_ascii=False)
        try:
            async with get_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE diag_sessions
                           SET phase = %s,
                               state_json = COALESCE(state_json, '{}'::jsonb) || %s::jsonb,
                               updated_at = NOW()
                         WHERE thread_id = %s
                        """,
                        (phase[:32], state_json, thread_id[:128]),
                    )
                await conn.commit()
        except Exception as e:
            raise AppError("更新诊断会话阶段失败", thread_id=thread_id, phase=phase) from e
    else:
        try:
            async with get_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        UPDATE diag_sessions
                           SET phase = %s, updated_at = NOW()
                         WHERE thread_id = %s
                        """,
                        (phase[:32], thread_id[:128]),
                    )
                await conn.commit()
        except Exception as e:
            raise AppError("更新诊断会话阶段失败", thread_id=thread_id, phase=phase) from e


async def update_session_state(thread_id: str, state_updates: dict) -> None:
    state_json = json.dumps(state_updates, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE diag_sessions
                       SET state_json = COALESCE(state_json, '{}'::jsonb) || %s::jsonb,
                           updated_at = NOW()
                     WHERE thread_id = %s
                    """,
                    (state_json, thread_id[:128]),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("更新诊断会话状态失败", thread_id=thread_id) from e


async def overwrite_session_state(thread_id: str, state_json: dict) -> None:
    raw = json.dumps(state_json, ensure_ascii=False)
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE diag_sessions
                       SET state_json = %s::jsonb, updated_at = NOW()
                     WHERE thread_id = %s
                    """,
                    (raw, thread_id[:128]),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("覆盖诊断会话状态失败", thread_id=thread_id) from e


async def get_sessions_by_tenant(tenant_id: str, limit: int = 100) -> list[dict]:
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT thread_id, tenant_id, store_id, phase, state_json,
                           trigger_type, created_at, updated_at
                    FROM diag_sessions
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (tenant_id[:32], limit),
                )
                return await cur.fetchall()
    except Exception as e:
        raise AppError("查询租户诊断会话列表失败", tenant_id=tenant_id) from e


async def delete_session(thread_id: str) -> None:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM diag_sessions WHERE thread_id = %s",
                    (thread_id[:128],),
                )
            await conn.commit()
    except Exception as e:
        raise AppError("删除诊断会话失败", thread_id=thread_id) from e
