"""wlwq 模拟业务系统 FastAPI 应用 — 供 MCP 调用，连接 MySQL wlwq-enterprise-service。"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging_setup import setup_logging
from src.wlwq.database import close_pool, get_pool
from src.wlwq.db_schema import ensure_wlwq_tables
from src.wlwq.routes import client_record, coupon, examine_initiate, exec_task, message, mock_stats, sales_contract, store, sys

setup_logging("wlwq")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="wlwq 模拟业务系统",
    description="企业服务 API，供 MCP 调用，数据来自 MySQL wlwq-enterprise-service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(store.router)
app.include_router(exec_task.router)
app.include_router(message.router)
app.include_router(client_record.router)
app.include_router(sales_contract.router)
app.include_router(examine_initiate.router)
app.include_router(coupon.router)
app.include_router(sys.router)
app.include_router(mock_stats.router)


@app.on_event("startup")
async def startup():
    await get_pool()
    await ensure_wlwq_tables()


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "wlwq-enterprise-service"}
