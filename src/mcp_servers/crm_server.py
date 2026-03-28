"""
crm-server: 客户数据与企业画像
传输: stdio
"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient
from src.mcp_servers.biz_scope import effective_store_id_for_biz

logger = logging.getLogger(__name__)

server = FastMCP("crm-server")
router = TenantRouter()
biz = BizAPIClient(router)


@server.tool()
async def get_store_profile(tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict:
    """
    获取企业/店铺画像信息。
    store_id 为空时返回企业级聚合画像（全企业诊断）。
    """
    logger.info("Tool called: get_store_profile tenant=%s store=%s", tenant_id, store_id)
    store_id = effective_store_id_for_biz(tenant_id, store_id)
    if not store_id:
        return await _get_tenant_profile(tenant_id, auth_token)

    store_data = await biz.get(tenant_id, f"/store/{store_id}", auth_token=auth_token)

    class_id = store_data.get("classId")
    class_data = {}
    if class_id:
        class_data = await biz.get(tenant_id, f"/store-class/{class_id}", auth_token=auth_token)

    return {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "store_name": store_data.get("storeName", ""),
        "store_type": store_data.get("storeType", ""),
        "business_mode": store_data.get("businessMode", "mall"),
        "industry_code": class_data.get("classCode", store_data.get("industryCode", "")),
        "industry_name": class_data.get("className", ""),
        "province": store_data.get("province", ""),
        "city": store_data.get("city", ""),
        "county": store_data.get("county", ""),
        "customer_count": store_data.get("customerCount", 0),
        "monthly_gmv": store_data.get("monthlyGmv", 0),
        "employee_count": store_data.get("employeeCount", 0),
        "created_days": store_data.get("createdDays", 0),
        "admin_account_ids": store_data.get("adminAccountIds", []),
    }


async def _get_tenant_profile(tenant_id: str, auth_token: str | None = None) -> dict:
    """调用 /store/list 获取全部店铺，聚合为企业级画像。"""
    store_list_data = await biz.get(tenant_id, "/store/list", auth_token=auth_token)
    stores = store_list_data.get("list", [])
    tenant_name, industry_code = await router.get_tenant_basic_info(tenant_id)

    all_admin_ids: list[str] = []
    total_customers = 0
    total_gmv = 0.0
    total_employees = 0
    store_names: list[str] = []
    business_modes: set[str] = set()
    for s in stores:
        store_names.append(s.get("storeName", s.get("storeId", "")))
        total_customers += s.get("customerCount", 0)
        total_gmv += s.get("monthlyGmv", 0)
        total_employees += s.get("employeeCount", 0)
        all_admin_ids.extend(s.get("adminAccountIds", []))
        bm = s.get("businessMode", "")
        if bm:
            business_modes.add(bm)
        if not industry_code:
            industry_code = s.get("industryCode", "")

    return {
        "tenant_id": tenant_id,
        "store_id": "",
        "store_name": f"{tenant_name}（全企业）",
        "store_type": "enterprise",
        "business_mode": business_modes.pop() if len(business_modes) == 1 else "hybrid",
        "industry_code": industry_code,
        "industry_name": "",
        "province": "",
        "city": "",
        "county": "",
        "customer_count": total_customers,
        "monthly_gmv": total_gmv,
        "employee_count": total_employees,
        "created_days": 0,
        "admin_account_ids": list(set(all_admin_ids)),
        "scope": "enterprise",
        "store_count": len(stores),
        "store_names": store_names,
        "stores": [{"store_id": s.get("storeId"), "store_name": s.get("storeName")} for s in stores],
    }


@server.tool()
async def get_customer_list(
    tenant_id: str,
    store_id: str,
    filter_type: str = "all",
    page: int = 1,
    page_size: int = 20,
    auth_token: str | None = None,
) -> dict:
    """获取客户列表（支持分类筛选: all | high_value | churn_risk | new）。"""
    logger.info(
        "Tool called: get_customer_list tenant=%s store=%s filter=%s page=%s", tenant_id, store_id, filter_type, page
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    req: dict = {
        "storeId": sid,
        "filterType": filter_type,
        "pageNo": page,
        "pageSize": page_size,
    }
    data = await biz.get(tenant_id, "/client-record/list", req, auth_token=auth_token)
    return {
        "total": data.get("total", 0),
        "items": data.get("list", []),
    }


@server.tool()
async def get_customer_detail(tenant_id: str, client_record_id: str, auth_token: str | None = None) -> dict:
    """获取单个客户详情（含交易记录、跟进记录）。"""
    logger.info("Tool called: get_customer_detail tenant=%s client_id=%s", tenant_id, client_record_id)
    import asyncio

    client_data, contracts = await asyncio.gather(
        biz.get(tenant_id, f"/client-record/{client_record_id}", auth_token=auth_token),
        biz.get(tenant_id, "/sales-contract/list", {"clientRecordId": client_record_id}, auth_token=auth_token),
    )
    client_data["contracts"] = contracts.get("list", [])
    return client_data


@server.tool()
async def get_sales_contract_list(
    tenant_id: str,
    client_record_id: str | None = None,
    auth_token: str | None = None,
) -> dict:
    """GET /sales-contract/list — 销售合同列表（可选按客户筛选）。"""
    logger.info("Tool called: get_sales_contract_list tenant=%s client_id=%s", tenant_id, client_record_id)
    req: dict = {}
    if client_record_id:
        req["clientRecordId"] = client_record_id
    data = await biz.get(tenant_id, "/sales-contract/list", req, auth_token=auth_token)
    return {"total": data.get("total", 0), "items": data.get("list", [])}


@server.tool()
async def get_order_analytics(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
    group_by: str = "day",
    auth_token: str | None = None,
) -> dict:
    """获取订单分析数据（GMV趋势、客单价、品类分布）。"""
    logger.info(
        "Tool called: get_order_analytics tenant=%s store=%s period=%s~%s group_by=%s",
        tenant_id,
        store_id,
        start_date,
        end_date,
        group_by,
    )
    sid = effective_store_id_for_biz(tenant_id, store_id)
    req: dict = {
        "storeId": sid,
        "startDate": start_date,
        "endDate": end_date,
        "groupBy": group_by,
    }
    data = await biz.get(tenant_id, "/store-order/analytics", req, auth_token=auth_token)
    return data


async def _sys_dept_tree(tenant_id: str, store_id: str, auth_token: str | None = None) -> dict:
    # 业务网关常见：{ code, msg, data: [ {...}, ... ] }，biz.get 会解包为 list；此处统一成含 list 的 dict
    raw = await biz.get(tenant_id, "/sys-dept/tree", {"storeId": store_id}, auth_token=auth_token)
    if isinstance(raw, list):
        return {"list": raw}
    if isinstance(raw, dict):
        return raw
    return {"list": []}


@server.tool()
async def get_dept_tree(tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict:
    """GET /sys-dept/tree — 部门树。"""
    logger.info("Tool called: get_dept_tree tenant=%s store=%s", tenant_id, store_id)
    sid = effective_store_id_for_biz(tenant_id, store_id)
    return await _sys_dept_tree(tenant_id, sid, auth_token)


@server.tool()
async def get_users_by_dept(tenant_id: str, dept_id: str, auth_token: str | None = None) -> dict:
    """GET /sys-user/list — 部门下用户列表。"""
    logger.info("Tool called: get_users_by_dept tenant=%s dept_id=%s", tenant_id, dept_id)
    data = await biz.get(tenant_id, "/sys-user/list", {"deptId": dept_id}, auth_token=auth_token)
    return {"list": data.get("list", [])}


@server.tool()
async def get_dept_structure(tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict:
    """获取部门架构与人员信息。store_id 为空时聚合所有店铺的部门树。"""
    logger.info("Tool called: get_dept_structure tenant=%s store=%s", tenant_id, store_id)
    sid = effective_store_id_for_biz(tenant_id, store_id)
    if sid:
        return await _fetch_dept_tree(tenant_id, sid, auth_token)

    store_list_data = await biz.get(tenant_id, "/store/list", auth_token=auth_token)
    stores = store_list_data.get("list", [])
    if not stores:
        return {"store_id": "", "departments": []}

    import asyncio

    trees = await asyncio.gather(*[_fetch_dept_tree(tenant_id, s.get("storeId", ""), auth_token) for s in stores])
    seen_ids: set[str] = set()
    merged: list[dict] = []
    for tree in trees:
        for dept in tree.get("departments", []):
            did = dept.get("dept_id")
            if did and did not in seen_ids:
                seen_ids.add(did)
                merged.append(dept)
    return {"store_id": "", "departments": merged}


async def _fetch_dept_tree(tenant_id: str, store_id: str, auth_token: str | None = None) -> dict:
    # 业务约定：query 始终带 storeId（单店非空；来自列表聚合时与业务数据一致）
    dept_tree = await _sys_dept_tree(tenant_id, store_id, auth_token)
    raw_list = dept_tree.get("list") or dept_tree.get("children") or []
    departments = []
    for dept in raw_list:
        dept_id = dept.get("deptId", dept.get("id"))
        users_data = await biz.get(tenant_id, "/sys-user/list", {"deptId": dept_id}, auth_token=auth_token)
        users = users_data.get("list") or []
        departments.append(
            {
                "dept_id": dept_id,
                "dept_name": dept.get("deptName", dept.get("name", "")),
                "parent_id": dept.get("parentId"),
                "users": users,
            }
        )
    return {"store_id": store_id, "departments": departments}


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
