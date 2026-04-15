"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.constants import API_PREFIX
from src.api.routes import diagnosis, solutions, sys_config, track, review, ws, mcp
from src.api.routes import compat_enterprises, compat_diagnosis, compat_dimensions, compat_solutions, compat_ws, compat_execution, compat_tracking
from src.agent.tools import close_all_sessions as close_mcp_sessions
from src.runtime.graph_app import get_graph_app, reset_graph_app
from src.api.token_sync import sync_request_tokens_dependency
from src.core.db_pool import open_pool, close_pool
from src.core.db_init import run_alembic_upgrade
from src.core.logging_setup import setup_logging
from src.core.config import log_diagnosis_service_config
from src.scheduler.weekly_diagnosis import start_scheduler
from src.worker.reconcile import reconcile_pending_jobs

logger = logging.getLogger(__name__)

setup_logging("ops-brain")
log_diagnosis_service_config(logger, prefix="ops-brain 启动")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await open_pool()
    await run_alembic_upgrade()
    await get_graph_app()
    app.state.scheduler = start_scheduler()

    from src.runtime.diagnosis_ws_manager import manager as diag_manager

    compat_ws.install_enterprise_bridge(diag_manager)
    await reconcile_pending_jobs()
    try:
        yield
    finally:
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler is not None:
            try:
                scheduler.shutdown(wait=False)
            except Exception as e:
                logger.warning("关闭定时任务调度器失败: %s", e)
        await close_mcp_sessions()
        await reset_graph_app()
        await close_pool()


app = FastAPI(
    title="企业运营AI智能诊断系统",
    description="基多租户 SaaS 智能诊断服务",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix=API_PREFIX)
_token_sync_dep = [Depends(sync_request_tokens_dependency)]

api_router.include_router(diagnosis.router, dependencies=_token_sync_dep)
api_router.include_router(solutions.router, dependencies=_token_sync_dep)
api_router.include_router(track.router, dependencies=_token_sync_dep)
api_router.include_router(review.router, dependencies=_token_sync_dep)
api_router.include_router(sys_config.router, dependencies=_token_sync_dep)
api_router.include_router(ws.router)
api_router.include_router(mcp.router, dependencies=_token_sync_dep)

# 前端兼容层路由（优先匹配，放在原始路由之后即可，因为路径不冲突）
api_router.include_router(compat_enterprises.router, dependencies=_token_sync_dep)
api_router.include_router(compat_diagnosis.router, dependencies=_token_sync_dep)
api_router.include_router(compat_dimensions.router, dependencies=_token_sync_dep)
api_router.include_router(compat_solutions.router, dependencies=_token_sync_dep)
api_router.include_router(compat_execution.router, dependencies=_token_sync_dep)
api_router.include_router(compat_tracking.router, dependencies=_token_sync_dep)
api_router.include_router(compat_ws.router)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ops-brain"}
