"""thread_id ↔ enterprise_id（tenant_id）映射，供企业级 WS 与诊断列表等使用。"""

from __future__ import annotations

from datetime import datetime, timezone

from src.runtime.running_tasks import running_tasks

_thread_to_enterprise: dict[str, str] = {}


def _thread_sort_key(thread_id: str) -> tuple[int, str]:
    """优先按 thread_id 中的时间戳排序，无法解析时降级到最小值。"""
    if thread_id.startswith("diag_"):
        try:
            ts = thread_id.split("_", 2)[1]
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            return int(dt.replace(tzinfo=timezone.utc).timestamp()), thread_id
        except (IndexError, ValueError):
            pass
    return 0, thread_id


def register_thread_enterprise(thread_id: str, enterprise_id: str) -> None:
    """注册 thread_id → enterprise_id 映射（启动诊断时调用）。"""
    _thread_to_enterprise[thread_id] = enterprise_id


def get_thread_enterprise(thread_id: str) -> str | None:
    """获取 thread_id 对应的 enterprise_id。"""
    return _thread_to_enterprise.get(thread_id)


def unregister_thread(thread_id: str) -> None:
    _thread_to_enterprise.pop(thread_id, None)


async def get_running_threads_for_enterprise(enterprise_id: str) -> list[str]:
    """返回属于指定 enterprise 的所有正在运行的 thread_id 列表。"""
    remote = await running_tasks.get_running_threads_for_tenant(enterprise_id)
    local = []
    for tid, eid in _thread_to_enterprise.items():
        if eid != enterprise_id:
            continue
        if await running_tasks.is_running(tid):
            local.append(tid)
    merged = set(local)
    merged.update(remote)
    return sorted(merged, key=_thread_sort_key, reverse=True)


async def get_active_diagnosis_thread_for_tenant(enterprise_id: str) -> str | None:
    """该企业是否已有未结束的诊断任务（跨实例）。"""
    active = await running_tasks.get_active_thread_for_tenant(enterprise_id)
    if active:
        return active
    for tid in await get_running_threads_for_enterprise(enterprise_id):
        t = running_tasks.get(tid)
        if t is not None and not t.done():
            return tid
    return None
