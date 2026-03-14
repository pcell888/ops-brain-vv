"""FastAPI 应用入口。"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import diagnosis, ws
from src.agent.graph import close_checkpointer
from src.agent.tools import close_all_sessions as close_mcp_sessions
from src.core.db_init import ensure_tenant_registry
from src.wlwq.database import close_pool as wlwq_close_pool, get_pool as wlwq_get_pool
from src.wlwq.routes import client_record, examine_initiate, mock_stats, sales_contract

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="企业运营AI智能诊断系统",
    description="基于 LangGraph + MCP 的多租户 SaaS 智能诊断服务",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnosis.router)
app.include_router(ws.router)
app.include_router(client_record.router)
app.include_router(sales_contract.router)
app.include_router(examine_initiate.router)
app.include_router(mock_stats.router)


@app.on_event("startup")
async def startup():
    await ensure_tenant_registry()
    await wlwq_get_pool()


@app.on_event("shutdown")
async def shutdown():
    await close_mcp_sessions()
    await close_checkpointer()
    await wlwq_close_pool()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ops-brain"}
