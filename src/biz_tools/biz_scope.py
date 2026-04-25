"""业务 API 查询范围 — tenant 与店铺维度。"""

from __future__ import annotations


def effective_store_id_for_biz(tenant_id: str, store_id: str | None) -> str:
    s = (store_id or "").strip()
    if not s or s == tenant_id:
        return ""
    return s
