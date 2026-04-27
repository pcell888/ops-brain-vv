"""业务模拟路径路由 — CRM 路由用 handlers 的 _raw_*，与工具层共用数据源。"""

from __future__ import annotations

from typing import Any, Callable

from src.biz.http_client import HTTPClientError
from src.biz.mock.handlers import client_sales_examine
from src.biz.mock.handlers.stats import store_order_analytics
from src.biz.mock import crm_handlers, metrics_handlers, notify_handlers, task_handlers

_Handler = Callable[[str, str, dict[str, Any], dict[str, Any]], dict[str, Any] | None]


def _dispatch_crm_raw(method: str, path: str, q: dict[str, Any], body: dict[str, Any]) -> dict[str, Any] | None:
    m = method.upper()
    if m == "GET" and path == "store/list":
        return crm_handlers._raw_store_list()
    if m == "GET" and path.startswith("store-class/"):
        return crm_handlers._raw_store_class(path.split("/", 1)[1])
    if m == "GET" and path.startswith("store/") and path != "store/list":
        return crm_handlers._raw_store_detail(path.split("/", 1)[1])
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
        return crm_handlers._raw_dept_tree(q.get("storeId"))
    if m == "GET" and path == "sys-user/list":
        return crm_handlers._raw_user_list(q.get("deptId"))
    _ = body
    return None


_DOMAIN_HANDLERS: tuple[tuple[str, _Handler], ...] = (
    ("metrics", metrics_handlers.try_raw_request),
    ("crm", _dispatch_crm_raw),
    ("notify", notify_handlers.try_raw_request),
    ("task", task_handlers.try_raw_request),
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

    raise HTTPClientError(404, f"业务模拟未实现: {m} /{p}", path)