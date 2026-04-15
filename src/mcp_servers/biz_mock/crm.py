"""CRM / 企业画像 — 与 biz/crm.py 同名、同签名、同 register；进程内模拟（wlwq_local 由 BizAPIClient 分流）。"""

from __future__ import annotations

import asyncio
import logging

from mcp.server import FastMCP

from src.mcp_servers.biz_scope import effective_store_id_for_biz
from src.mcp_servers.biz_mock import client_sales_examine
from src.mcp_servers.biz_mock.stats import store_order_analytics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 与业务侧 JSON 一致的模拟 data（供本模块工具与 dispatch 复用）
# ---------------------------------------------------------------------------


def _raw_store_list() -> dict:
    return {
        "list": [
            {
                "storeId": "s001",
                "storeName": "杭州旗舰店",
                "storeType": "retail",
                "industryCode": "retail_general",
                "province": "浙江省",
                "city": "杭州市",
                "customerCount": 3280,
                "monthlyGmv": 425000,
                "employeeCount": 18,
                "adminAccountIds": ["admin-001", "admin-002"],
            },
            {
                "storeId": "s002",
                "storeName": "上海体验店",
                "storeType": "retail",
                "industryCode": "retail_general",
                "province": "上海市",
                "city": "上海市",
                "customerCount": 2150,
                "monthlyGmv": 310000,
                "employeeCount": 12,
                "adminAccountIds": ["admin-003"],
            },
        ]
    }


def _raw_store_detail(_store_id: str) -> dict:
    _ = _store_id
    return {
        "storeName": "AI示范店",
        "storeType": "retail",
        "businessMode": "mall",
        "classId": "CLS001",
        "industryCode": "retail_general",
        "province": "浙江省",
        "city": "杭州市",
        "county": "西湖区",
        "customerCount": 3280,
        "monthlyGmv": 425000,
        "employeeCount": 18,
        "createdDays": 540,
        "adminAccountIds": ["admin-001", "admin-002"],
    }


def _raw_store_class(_class_id: str) -> dict:
    _ = _class_id
    return {"classCode": "retail_general", "className": "综合零售"}


def _raw_dept_tree(_store_id: str | None) -> dict:
    _ = _store_id
    return {
        "list": [
            {"deptId": 1, "deptName": "总公司", "parentId": 0},
            {"deptId": 2, "deptName": "销售部", "parentId": 1},
            {"deptId": 3, "deptName": "运营部", "parentId": 1},
            {"deptId": 4, "deptName": "客服部", "parentId": 1},
        ]
    }


def _raw_user_list(dept_id: str | None) -> dict:
    base = [
        {"userId": 1, "userName": "管理员", "deptId": 2},
        {"userId": 2, "userName": "销售主管", "deptId": 2},
        {"userId": 3, "userName": "运营经理", "deptId": 3},
        {"userId": 4, "userName": "客服主管", "deptId": 4},
    ]
    if dept_id and str(dept_id).isdigit():
        d = int(dept_id)
        return {"list": [u for u in base if u["deptId"] == d]}
    return {"list": base}


# ---------------------------------------------------------------------------
# 与 biz/crm.py 对齐的 MCP 工具实现
# ---------------------------------------------------------------------------


async def get_store_profile(tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict:
    """
    获取企业/店铺画像信息。
    store_id 为空时返回企业级聚合画像（全企业诊断）。
    """
    logger.info("Tool called: get_store_profile tenant=%s store=%s", tenant_id, store_id)
    _ = auth_token
    store_id = effective_store_id_for_biz(tenant_id, store_id)
    if not store_id:
        return await _get_tenant_profile(tenant_id, auth_token)

    store_data = _raw_store_detail(store_id)
    class_id = store_data.get("classId")
    class_data: dict = {}
    if class_id:
        class_data = _raw_store_class(class_id)

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
    """模拟 /store/list 聚合企业级画像。"""
    _ = auth_token
    store_list_data = _raw_store_list()
    stores = store_list_data.get("list", [])
    tenant_name, industry_code = "本地业务模拟", "retail_general"

    all_admin_ids: list[str] = []
    total_customers = 0
    total_gmv = 0.0
    total_employees = 0
    store_names: list[str] = []
    business_modes: set[str] = set()
    for s in stores:
        store_names.append(s.get("storeName", s.get("storeId", "")))
        total_customers += s.get("customerCount", 0)
        total_gmv += float(s.get("monthlyGmv", 0))
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
        "Tool called: get_customer_list tenant=%s store=%s filter=%s page=%s",
        tenant_id,
        store_id,
        filter_type,
        page,
    )
    _ = auth_token
    sid = effective_store_id_for_biz(tenant_id, store_id)
    req: dict = {
        "storeId": sid,
        "filterType": filter_type,
        "pageNo": page,
        "pageSize": page_size,
    }
    data = client_sales_examine.client_record_list(req)
    return {
        "total": data.get("total", 0),
        "items": data.get("list", []),
    }


async def get_customer_detail(tenant_id: str, client_record_id: str, auth_token: str | None = None) -> dict:
    """获取单个客户详情（含交易记录、跟进记录）。"""
    logger.info("Tool called: get_customer_detail tenant=%s client_id=%s", tenant_id, client_record_id)
    _ = auth_token

    async def _client():
        return client_sales_examine.client_record_detail(client_record_id)

    async def _contracts():
        return client_sales_examine.sales_contract_list({"clientRecordId": client_record_id})

    client_data, contracts = await asyncio.gather(_client(), _contracts())
    client_data = dict(client_data)
    client_data["contracts"] = contracts.get("list", [])
    return client_data


async def get_sales_contract_list(
    tenant_id: str,
    client_record_id: str | None = None,
    auth_token: str | None = None,
) -> dict:
    """GET /sales-contract/list — 销售合同列表（可选按客户筛选）。"""
    logger.info("Tool called: get_sales_contract_list tenant=%s client_id=%s", tenant_id, client_record_id)
    _ = auth_token
    req: dict = {}
    if client_record_id:
        req["clientRecordId"] = client_record_id
    data = client_sales_examine.sales_contract_list(req)
    return {"total": data.get("total", 0), "items": data.get("list", [])}


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
    _ = auth_token
    sid = effective_store_id_for_biz(tenant_id, store_id)
    req: dict = {
        "storeId": sid,
        "startDate": start_date,
        "endDate": end_date,
        "groupBy": group_by,
    }
    return store_order_analytics(req)


async def _sys_dept_tree(tenant_id: str, store_id: str, auth_token: str | None = None) -> dict:
    _ = tenant_id, auth_token
    return _raw_dept_tree(store_id)


async def get_dept_tree(tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict:
    """GET /sys-dept/tree — 部门树。"""
    logger.info("Tool called: get_dept_tree tenant=%s store=%s", tenant_id, store_id)
    sid = effective_store_id_for_biz(tenant_id, store_id)
    return await _sys_dept_tree(tenant_id, sid, auth_token)


async def get_users_by_dept(tenant_id: str, dept_id: str, auth_token: str | None = None) -> dict:
    """GET /sys-user/list — 部门下用户列表。"""
    logger.info("Tool called: get_users_by_dept tenant=%s dept_id=%s", tenant_id, dept_id)
    _ = auth_token
    data = _raw_user_list(dept_id)
    return {"list": data.get("list", [])}


async def get_dept_structure(tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict:
    """获取部门架构与人员信息。store_id 为空时聚合所有店铺的部门树。"""
    logger.info("Tool called: get_dept_structure tenant=%s store=%s", tenant_id, store_id)
    sid = effective_store_id_for_biz(tenant_id, store_id)
    if sid:
        return await _fetch_dept_tree(tenant_id, sid, auth_token)

    store_list_data = _raw_store_list()
    stores = store_list_data.get("list", [])
    if not stores:
        return {"store_id": "", "departments": []}

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
    dept_tree = await _sys_dept_tree(tenant_id, store_id, auth_token)
    raw_list = dept_tree.get("list") or dept_tree.get("children") or []
    departments = []
    for dept in raw_list:
        dept_id = dept.get("deptId", dept.get("id"))
        users_data = _raw_user_list(str(dept_id) if dept_id is not None else None)
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


def register(server: FastMCP) -> None:
    """与 biz/crm.register 相同的工具集合；可选独立 mock MCP 进程使用。"""
    for fn in (
        get_store_profile,
        get_customer_list,
        get_customer_detail,
        get_sales_contract_list,
        get_order_analytics,
        get_dept_tree,
        get_users_by_dept,
        get_dept_structure,
    ):
        server.add_tool(fn)
