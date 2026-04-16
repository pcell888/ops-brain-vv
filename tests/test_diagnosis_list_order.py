from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.runtime import thread_enterprise
from src.services import diagnosis_service


@pytest.mark.asyncio
async def test_get_running_threads_for_enterprise_sorted_by_thread_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread_enterprise.register_thread_enterprise("diag_20260416143008_old", "e1")
    thread_enterprise.register_thread_enterprise("diag_20260416145805_new", "e1")

    async def _remote(_enterprise_id: str) -> list[str]:
        return []

    async def _is_running(_thread_id: str) -> bool:
        return True

    monkeypatch.setattr(thread_enterprise.running_tasks, "get_running_threads_for_tenant", _remote)
    monkeypatch.setattr(thread_enterprise.running_tasks, "is_running", _is_running)

    try:
        tids = await thread_enterprise.get_running_threads_for_enterprise("e1")
        assert tids == ["diag_20260416145805_new", "diag_20260416143008_old"]
    finally:
        thread_enterprise.unregister_thread("diag_20260416143008_old")
        thread_enterprise.unregister_thread("diag_20260416145805_new")


@pytest.mark.asyncio
async def test_diagnosis_list_respects_limit_after_merge_running_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older_db = datetime(2026, 4, 16, 14, 3, 8, tzinfo=timezone.utc)

    async def _list_reports(_tenant_id: str | None, _store_id: str | None, _page: int, _limit: int):
        return (
            [
                {
                    "thread_id": "diag_20260416143008_db",
                    "tenant_id": "e1",
                    "store_id": "",
                    "trigger_type": "manual",
                    "created_at": older_db,
                }
            ],
            1,
        )

    async def _running_threads(_enterprise_id: str) -> list[str]:
        # 故意返回乱序，确保服务层排序稳定
        return ["diag_20260416143008_old", "diag_20260416145805_new"]

    async def _is_running(_thread_id: str) -> bool:
        return True

    async def _build_running_item(tid: str) -> dict:
        if tid.endswith("new"):
            created_at = "2026-04-16T14:58:05+08:00"
        else:
            created_at = "2026-04-16T14:30:08+08:00"
        return {
            "diagnosis_id": tid,
            "name": "诊断",
            "status": "running",
            "progress": 10,
            "message": "running",
            "error_message": None,
            "health_score": None,
            "anomaly_count": None,
            "report_ready": False,
            "trigger_type": "manual",
            "created_at": created_at,
        }

    async def _build_db_item(thread_id: str, _row: dict) -> dict:
        return {
            "diagnosis_id": thread_id,
            "name": "诊断",
            "status": "completed",
            "progress": 100,
            "message": "done",
            "error_message": None,
            "health_score": 80.0,
            "anomaly_count": 1,
            "report_ready": True,
            "trigger_type": "manual",
            "created_at": "2026-04-16T14:03:08+08:00",
        }

    monkeypatch.setattr(diagnosis_service, "list_reports", _list_reports)
    monkeypatch.setattr(diagnosis_service, "get_running_threads_for_enterprise", _running_threads)
    monkeypatch.setattr(diagnosis_service.running_tasks, "is_running", _is_running)
    monkeypatch.setattr(diagnosis_service, "_build_running_item", _build_running_item)
    monkeypatch.setattr(diagnosis_service, "_build_list_item_from_row", _build_db_item)

    items, total = await diagnosis_service.get_diagnosis_list_items(
        tenant_id="e1",
        skip=0,
        limit=1,
        store_id=None,
        include_running=True,
    )

    assert total == 3
    assert len(items) == 1
    assert items[0]["diagnosis_id"] == "diag_20260416145805_new"
