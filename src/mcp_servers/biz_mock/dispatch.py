"""BizAPIClient 在 wlwq_local 时的 path 模拟；CRM 路由用 biz_mock.crm 的 _raw_*，与工具层共用数据源。"""

from __future__ import annotations

from typing import Any, Callable

from src.mcp_servers.biz_api_client import BizAPIError
from src.mcp_servers.biz_mock import client_sales_examine, crm, metrics, notify, task
from src.mcp_servers.biz_mock.stats import store_order_analytics

_Handler = Callable[[str, str, dict[str, Any], dict[str, Any]], dict[str, Any] | None]


def _dispatch_crm_raw(method: str, path: str, q: dict[str, Any], body: dict[str, Any]) -> dict[str, Any] | None:
    m = method.upper()
    if m == "GET" and path == "store/list":
        return crm._raw_store_list()
    if m == "GET" and path.startswith("store-class/"):
        return crm._raw_store_class(path.split("/", 1)[1])
    if m == "GET" and path.startswith("store/") and path != "store/list":
        return crm._raw_store_detail(path.split("/", 1)[1])
    if m == "GET" and path == "client-record/list":
        return client_sales_examine.client_record_list(q)
    if m == "GET" and path.startswith("client-record/"):
        tail = path.split("/", 1)[1]
        if tail in ("statistics", "list"):
            return None
        return client_sales_examine.client_record_detail(tail)
    if m == "GET" and path == "sales-contract/list":
        return client_sales_examine.sales_contract_list(q)
    if m == "GET" and path == "store-order/analytics":
        return store_order_analytics(q)
    if m == "GET" and path == "sys-dept/tree":
        return crm._raw_dept_tree(q.get("storeId"))
    if m == "GET" and path == "sys-user/list":
        return crm._raw_user_list(q.get("deptId"))
    _ = body
    return None


# 顺序重要：metrics 须先于 crm，避免 client-record/statistics 被当成单条 id
_DOMAIN_HANDLERS: tuple[tuple[str, _Handler], ...] = (
    ("metrics", metrics.try_raw_request),
    ("crm", _dispatch_crm_raw),
    ("notify", notify.try_raw_request),
    ("task", task.try_raw_request),
)


def _norm_path(path: str) -> str:
    p = (path or "").strip()
    if p.startswith("/"):
        p = p[1:]
    return p.rstrip("/")


async def dispatch_biz_mock(
    method: str,
    path: str,
    params: dict[str, Any] | None,
    json_data: dict[str, Any] | None,
) -> dict[str, Any]:
    m = (method or "GET").upper()
    p = _norm_path(path)
    q: dict[str, Any] = dict(params or {})
    body = json_data or {}

    for _name, handler in _DOMAIN_HANDLERS:
        result = handler(m, p, q, body)
        if result is not None:
            return result

    raise BizAPIError(404, f"业务模拟未实现: {m} /{p}", path)
