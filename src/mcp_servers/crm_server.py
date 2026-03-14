"""
crm-server: 客户数据与企业画像
传输: stdio
"""

from __future__ import annotations

import logging

from mcp.server import FastMCP

from src.mcp_servers.tenant_router import TenantRouter
from src.mcp_servers.biz_api_client import BizAPIClient

logger = logging.getLogger(__name__)

server = FastMCP("crm-server")
router = TenantRouter()
biz = BizAPIClient(router)


@server.tool()
async def get_store_profile(tenant_id: str, store_id: str) -> dict:
    """
    获取企业/店铺画像信息。
    返回: store_id, store_name, store_type, industry_code, industry_name,
          province, city, county, customer_count, monthly_gmv, employee_count, created_days
    """
    store_data = await biz.get(tenant_id, f"/store/{store_id}")

    class_id = store_data.get("classId")
    class_data = {}
    if class_id:
        class_data = await biz.get(tenant_id, f"/store-class/{class_id}")

    return {
        "tenant_id": tenant_id,
        "store_id": store_id,
        "store_name": store_data.get("storeName", ""),
        "store_type": store_data.get("storeType", ""),
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


@server.tool()
async def get_customer_list(
    tenant_id: str,
    store_id: str,
    filter_type: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """获取客户列表（支持分类筛选: all | high_value | churn_risk | new）。"""
    data = await biz.get(tenant_id, "/client-record/list", {
        "storeId": store_id,
        "filterType": filter_type,
        "page": page,
        "pageSize": page_size,
    })
    return {
        "total": data.get("total", 0),
        "items": data.get("list", []),
    }


@server.tool()
async def get_customer_detail(tenant_id: str, client_record_id: str) -> dict:
    """获取单个客户详情（含交易记录、跟进记录）。"""
    import asyncio
    client_data, contracts = await asyncio.gather(
        biz.get(tenant_id, f"/client-record/{client_record_id}"),
        biz.get(tenant_id, "/sales-contract/list", {"clientRecordId": client_record_id}),
    )
    client_data["contracts"] = contracts.get("list", [])
    return client_data


@server.tool()
async def get_order_analytics(
    tenant_id: str,
    store_id: str,
    start_date: str,
    end_date: str,
    group_by: str = "day",
) -> dict:
    """获取订单分析数据（GMV趋势、客单价、品类分布）。"""
    data = await biz.get(tenant_id, "/store-order/analytics", {
        "storeId": store_id,
        "startDate": start_date,
        "endDate": end_date,
        "groupBy": group_by,
    })
    return data


@server.tool()
async def get_dept_structure(tenant_id: str, store_id: str) -> dict:
    """获取企业部门架构与人员信息（用于任务分配匹配）。"""
    dept_tree = await biz.get(tenant_id, "/sys-dept/tree", {"storeId": store_id})

    departments = []
    for dept in dept_tree.get("list", dept_tree.get("children", [])):
        dept_id = dept.get("deptId", dept.get("id"))
        users_data = await biz.get(tenant_id, "/sys-user/list", {"deptId": dept_id})
        departments.append({
            "dept_id": dept_id,
            "dept_name": dept.get("deptName", dept.get("name", "")),
            "parent_id": dept.get("parentId"),
            "users": users_data.get("list", []),
        })

    return {"store_id": store_id, "departments": departments}


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
