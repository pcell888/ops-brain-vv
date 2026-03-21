"""FastAPI 应用入口。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.constants import API_PREFIX
from src.api.routes import diagnosis, solutions, sys_config, track, review, ws, mcp
from src.api.routes import compat_enterprises, compat_diagnosis, compat_dimensions, compat_solutions, compat_ws, compat_execution, compat_tracking
from src.agent.graph import close_checkpointer
from src.agent.tools import close_all_sessions as close_mcp_sessions
from src.core.db_init import (
    ensure_tenant_registry,
    ensure_ai_diagnosis_report,
    ensure_ai_push_log,
    ensure_ai_exec_task,
    ensure_ai_effect_tracking,
    ensure_ai_review_report,
)
from src.wlwq.database import close_pool as wlwq_close_pool, get_pool as wlwq_get_pool
from src.core.logging_setup import setup_logging

setup_logging("ops-brain")

app = FastAPI(
    title="企业运营AI智能诊断系统",
    description="基多租户 SaaS 智能诊断服务",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(diagnosis.router)
api_router.include_router(solutions.router)
api_router.include_router(track.router)
api_router.include_router(review.router)
api_router.include_router(sys_config.router)
api_router.include_router(ws.router)
api_router.include_router(mcp.router)

# 前端兼容层路由（优先匹配，放在原始路由之后即可，因为路径不冲突）
api_router.include_router(compat_enterprises.router)
api_router.include_router(compat_diagnosis.router)
api_router.include_router(compat_dimensions.router)
api_router.include_router(compat_solutions.router)
api_router.include_router(compat_execution.router)
api_router.include_router(compat_tracking.router)
api_router.include_router(compat_ws.router)

app.include_router(api_router)



@app.on_event("startup")
async def startup():
    await ensure_tenant_registry()
    await ensure_ai_diagnosis_report()
    await ensure_ai_push_log()
    await ensure_ai_exec_task()
    await ensure_ai_effect_tracking()
    await ensure_ai_review_report()
    await wlwq_get_pool()

    from src.api.deps import manager as diag_manager
    compat_ws.install_enterprise_bridge(diag_manager)


@app.on_event("shutdown")
async def shutdown():
    await close_mcp_sessions()
    await close_checkpointer()
    await wlwq_close_pool()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ops-brain"}
