"""业务 API 查询范围 — tenant 与店铺维度。"""

from __future__ import annotations


def effective_store_id_for_biz(tenant_id: str, store_id: str | None) -> str:
    """
    与业务侧约定：`storeId` 在请求中**始终携带**，**可为空字符串**（空 = 全企业汇总）。

    若调用方误将 tenant_id 填入 store_id，按全企业处理（返回空字符串）。
    """
    s = (store_id or "").strip()
    if not s or s == tenant_id:
        return ""
    return s
