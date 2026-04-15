"""数据库初始化入口。

统一通过 Alembic 管理 schema 变更，不再使用运行时手写 DDL。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

async def run_alembic_upgrade() -> None:
    """在 startup 时执行 `alembic upgrade head`。"""
    try:
        import asyncio
        import importlib

        command = importlib.import_module("alembic.command")
        Config = importlib.import_module("alembic.config").Config

        cfg = Config("alembic.ini")

        def _upgrade():
            command.upgrade(cfg, "head")

        await asyncio.to_thread(_upgrade)
        logger.info("Alembic 迁移执行成功 (upgrade head)")
    except Exception as e:
        logger.exception("Alembic 迁移失败")
        raise RuntimeError(f"数据库迁移失败：{e}。请先确认数据库可连通，或手动执行 alembic upgrade head") from e


async def _ensure_all_tables() -> None:
    """历史兼容空实现：schema 由 Alembic 统一管理。"""
    logger.warning("_ensure_all_tables 已废弃：请使用 Alembic 迁移")

async def ensure_tenant_registry():
    return None

async def ensure_ai_diagnosis_report():
    return None

async def ensure_ai_push_log():
    return None

async def ensure_ai_exec_task():
    return None

async def ensure_ai_pending_review():
    return None

async def ensure_ai_solution_knowledge():
    return None

async def ensure_ai_effect_snapshot():
    return None

async def ensure_ai_effect_tracking():
    return None

async def ensure_ai_review_report():
    return None
