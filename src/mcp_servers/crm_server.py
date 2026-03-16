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
async def get_store_profile(tenant_id: str, store_id: str = "") -> dict:
    """
    获取企业/店铺画像信息。
    store_id 为空时返回企业级聚合画像（全企业诊断）。
    """
    if not store_id:
        return await _get_tenant_profile(tenant_id)

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


async def _get_tenant_profile(tenant_id: str) -> dict:
    """从 tenant_registry.config 构建企业级画像。"""
    from src.core.tenant_config import get_tenant_config
    cfg = await get_tenant_config(tenant_id)
    stores = cfg.get("stores", [])
    store_names = [s.get("store_name", s.get("store_id", "")) for s in stores]

    import psycopg
    from src.core.config import get_settings
    settings = get_settings()
    async with await psycopg.AsyncConnection.connect(settings.postgres_uri) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT tenant_name, industry_code FROM tenant_registry WHERE tenant_id = %s",
                (tenant_id,),
            )
            row = await cur.fetchone()
    tenant_name = (row[0] if row else "") or ""
    industry_code = (row[1] if row else "") or ""

    return {
        "tenant_id": tenant_id,
        "store_id": "",
        "store_name": f"{tenant_name}（全企业）",
        "store_type": "enterprise",
        "industry_code": industry_code,
        "industry_name": "",
        "province": "",
        "city": "",
        "county": "",
        "customer_count": 0,
        "monthly_gmv": 0,
        "employee_count": cfg.get("team_size", 0),
        "created_days": 0,
        "admin_account_ids": [],
        "scope": "enterprise",
        "store_count": len(stores),
        "store_names": store_names,
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
    """获取企业部门架构与人员信息（用于任务分配匹配）。从 wlwq /sys-dept/tree、/sys-user/list 拉取。"""
    dept_tree = await biz.get(tenant_id, "/sys-dept/tree", {"storeId": store_id})
    raw_list = dept_tree.get("list") or dept_tree.get("children") or []
    departments = []
    for dept in raw_list:
        dept_id = dept.get("deptId", dept.get("id"))
        users_data = await biz.get(tenant_id, "/sys-user/list", {"deptId": dept_id})
        users = users_data.get("list") or []
        departments.append({
            "dept_id": dept_id,
            "dept_name": dept.get("deptName", dept.get("name", "")),
            "parent_id": dept.get("parentId"),
            "users": users,
        })
    return {"store_id": store_id, "departments": departments}


# ── stdio Transport ──────────────────────────────────────────────

if __name__ == "__main__":
    server.run(transport="stdio")
