"""效果追踪兼容层聚合路由。"""

from __future__ import annotations

from fastapi import APIRouter

from src.api.routes import (
    compat_tracking_analysis,
    compat_tracking_cases,
    compat_tracking_lifecycle,
    compat_tracking_report,
    compat_tracking_snapshot,
)

router = APIRouter(prefix="/tracking", tags=["效果追踪(兼容层)"])

router.include_router(compat_tracking_lifecycle.router)
router.include_router(compat_tracking_snapshot.router)
router.include_router(compat_tracking_report.router)
router.include_router(compat_tracking_cases.router)
router.include_router(compat_tracking_analysis.router)
