"""真实业务系统调用实现"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.biz.http_client import HTTPClient, HTTPClientError
from src.biz.router import TenantRouter, TenantNotFoundError
from src.biz.tenant_client import TenantClient
from src.biz.biz_constants import is_mock_tenant

logger = logging.getLogger(__name__)

_router = TenantRouter()
_http_clients: dict[str, HTTPClient] = {}


def _effective_store_id(tenant_id: str, store_id: str) -> str:
    s = (store_id or "").strip()
    if not s or s == tenant_id:
        return ""
    return s


def _get_http_client(tenant_id: str, base_url: str, headers: dict) -> HTTPClient:
    if tenant_id not in _http_clients:
        _http_clients[tenant_id] = HTTPClient(base_url, headers)
    return _http_clients[tenant_id]


async def _close_clients():
    for client in _http_clients.values():
        await client.close()
    _http_clients.clear()


class RealTenantClient(TenantClient):
    """真实业务系统调用"""
    
    def __init__(self, tenant_id: str):
        self._tenant_id = tenant_id
        self._ctx = None
        self._http: HTTPClient | None = None
    
    async def _ensure(self):
        if self._ctx is None:
            self._ctx = await _router.resolve(self._tenant_id)
            self._http = _get_http_client(
                self._ctx.tenant_id,
                self._ctx.api_base_url,
                self._ctx.auth_headers,
            )
    
    async def get_store_profile(self, tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        store_id = _effective_store_id(tenant_id, store_id)
        if not store_id:
            return await self._get_tenant_profile(auth_token)

        headers = {"Authorization": auth_token} if auth_token else None
        try:
            store_data = await self._http.get(f"/store/{store_id}", headers=headers)
        except HTTPClientError as e:
            if e.status_code == 404:
                logger.warning("store not found tenant=%s store_id=%s", tenant_id, store_id)
                return {
                    "tenant_id": tenant_id,
                    "store_id": store_id,
                    "store_name": "",
                    "store_type": "",
                    "business_mode": "hybrid",
                    "industry_code": "",
                    "industry_name": "",
                    "province": "",
                    "city": "",
                    "county": "",
                    "customer_count": 0,
                    "monthly_gmv": 0,
                    "employee_count": 0,
                    "created_days": 0,
                    "admin_account_ids": [],
                    "store_not_found": True,
                }
            raise

        class_id = store_data.get("classId")
        class_data = {}
        if class_id:
            class_data = await self._http.get(f"/store-class/{class_id}", headers=headers)

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

    async def _get_tenant_profile(self, auth_token: str | None = None) -> dict[str, Any]:
        headers = {"Authorization": auth_token} if auth_token else None
        store_list_data = await self._http.get("/store/list", headers=headers)
        stores = store_list_data.get("list", [])
        tenant_name = self._ctx.tenant_name
        industry_code = self._ctx.industry_code or ""

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
            "tenant_id": self._tenant_id,
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
    
    async def get_customer_list(self, tenant_id: str, store_id: str = "", filter_type: str = "all", page: int = 1, page_size: int = 20, auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        params = {"storeId": store_id, "filterType": filter_type, "pageNo": page, "pageSize": page_size}
        headers = {"Authorization": auth_token} if auth_token else None
        return await self._http.get("/client-record/list", params=params, headers=headers)
    
    async def get_customer_detail(self, tenant_id: str, client_record_id: str, auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        headers = {"Authorization": auth_token} if auth_token else None
        client_data, contracts = await asyncio.gather(
            self._http.get(f"/client-record/{client_record_id}", headers=headers),
            self._http.get("/sales-contract/list", params={"clientRecordId": client_record_id}, headers=headers),
        )
        client_data["contracts"] = contracts.get("list", [])
        return client_data
    
    async def get_sales_contract_list(self, tenant_id: str, client_record_id: str | None = None, auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        params = {"clientRecordId": client_record_id} if client_record_id else {}
        headers = {"Authorization": auth_token} if auth_token else None
        return await self._http.get("/sales-contract/list", params=params, headers=headers)
    
    async def get_order_analytics(self, tenant_id: str, store_id: str = "", start_date: str = "", end_date: str = "", group_by: str = "day", auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        params = {"storeId": store_id, "startDate": start_date, "endDate": end_date, "groupBy": group_by}
        headers = {"Authorization": auth_token} if auth_token else None
        return await self._http.get("/store-order/analytics", params=params, headers=headers)
    
    async def _sys_dept_tree(self, store_id: str, headers: dict | None) -> dict:
        raw = await self._http.get("/sys-dept/tree", params={"storeId": store_id}, headers=headers)
        if isinstance(raw, list):
            return {"list": raw}
        if isinstance(raw, dict):
            return raw
        return {"list": []}

    async def _fetch_dept_tree(self, store_id: str, headers: dict | None) -> dict:
        dept_tree = await self._sys_dept_tree(store_id, headers)
        raw_list = dept_tree.get("list") or dept_tree.get("children") or []
        departments = []
        for dept in raw_list:
            dept_id = dept.get("deptId", dept.get("id"))
            users_data = await self._http.get("/sys-user/list", params={"deptId": dept_id}, headers=headers)
            users = users_data.get("list") or []
            departments.append({
                "dept_id": dept_id,
                "dept_name": dept.get("deptName", dept.get("name", "")),
                "parent_id": dept.get("parentId"),
                "users": users,
            })
        return {"store_id": store_id, "departments": departments}

    async def get_dept_tree(self, tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        sid = _effective_store_id(tenant_id, store_id)
        headers = {"Authorization": auth_token} if auth_token else None
        return await self._sys_dept_tree(sid, headers)

    async def get_users_by_dept(self, tenant_id: str, dept_id: str, auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        headers = {"Authorization": auth_token} if auth_token else None
        data = await self._http.get("/sys-user/list", params={"deptId": dept_id}, headers=headers)
        return {"list": data.get("list", [])}

    async def get_dept_structure(self, tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict[str, Any]:
        await self._ensure()
        sid = _effective_store_id(tenant_id, store_id)
        headers = {"Authorization": auth_token} if auth_token else None
        if sid:
            return await self._fetch_dept_tree(sid, headers)

        store_list_data = await self._http.get("/store/list", headers=headers)
        stores = store_list_data.get("list", [])
        if not stores:
            return {"store_id": "", "departments": []}

        trees = await asyncio.gather(*[self._fetch_dept_tree(s.get("storeId", ""), headers) for s in stores])
        seen_ids: set[str] = set()
        merged: list[dict] = []
        for tree in trees:
            for dept in tree.get("departments", []):
                did = dept.get("dept_id")
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    merged.append(dept)
        return {"store_id": "", "departments": merged}
    
    async def create_execution_tasks(self, tenant_id: str, store_id: str = "", plan_id: str = "", tasks: list | None = None) -> dict[str, Any]:
        await self._ensure()
        payload = {"storeId": store_id, "planId": plan_id, "tasks": tasks or []}
        data = await self._http.post("/ai-diagnosis/exec-task/batch-create", json_data=payload)
        return {
            "plan_id": plan_id,
            "created_tasks": data.get("tasks", data.get("list", [])),
            "created_count": data.get("count", len(tasks or [])),
        }

    async def has_create_task_permission(
        self,
        tenant_id: str,
        user_id: int,
    ) -> dict[str, Any]:
        await self._ensure()
        data = await self._http.get("/ai-diagnosis/hasCreateTaskPermission", params={"userId": user_id})
        raw = data.get("hasPermission", data.get("has_permission", data.get("data", data)))
        if isinstance(raw, str):
            has_permission = raw.strip().lower() == "true"
        else:
            has_permission = bool(raw)
        return {"has_permission": has_permission}
    
    async def create_approval_flow(self, tenant_id: str, store_id: str = "", plan_id: str = "", title: str = "", content: str = "", approver_user_id: int = 0) -> dict[str, Any]:
        await self._ensure()
        payload = {"storeId": store_id, "title": title, "content": content, "approverUserId": approver_user_id, "bizType": "ai_diagnosis", "bizId": plan_id}
        data = await self._http.post("/examine-initiate/create", json_data=payload)
        return {"approval_id": data.get("id", ""), "status": "pending"}
    
    async def update_task_status(self, tenant_id: str, task_id: str = "", status: str = "", progress: float | None = None, remark: str | None = None) -> dict[str, Any]:
        await self._ensure()
        payload: dict = {"status": status}
        if progress is not None:
            payload["progress"] = progress
        if remark:
            payload["remark"] = remark
        data = await self._http.put(f"/ai-diagnosis/exec-task/{task_id}/status", json_data=payload)
        return {"task_id": task_id, "status": status, "updated": True, **data}
    
    async def create_coupon_campaign(self, tenant_id: str, store_id: str = "", campaign_config: dict | None = None) -> dict[str, Any]:
        await self._ensure()
        config = campaign_config or {}
        create_body = {"storeId": store_id, "couponName": config.get("coupon_name"), "couponType": config.get("coupon_type", 1), "startTime": config.get("start_time"), "endTime": config.get("end_time")}
        coupon_data = await self._http.post("/coupon/create", json_data=create_body)
        coupon_id = coupon_data.get("id") or coupon_data.get("couponId", "")
        dist_body = {"storeId": store_id, "couponId": coupon_id, "targetCustomers": config.get("target_customers", "all")}
        distribute_data = await self._http.post("/coupon/distribute", json_data=dist_body)
        return {"coupon_id": coupon_id, "distributed_count": distribute_data.get("count", 0), "campaign_config": config}
    
    async def create_seckill_activity(
        self,
        tenant_id: str,
        store_id: str = "",
        config: dict = None,
    ) -> dict[str, Any]:
        if config is None:
            config = {}
        await self._ensure()
        body = dict(config)
        body["storeId"] = store_id
        data = await self._http.post("/seckill-apply/create", json_data=body)
        return {"activity_id": data.get("id", ""), "status": "created"}
    
    def _num(self, v, default: float | int = 0):
        return default if v is None else v

    def _store_aware_params(self, tenant_id: str, store_id: str, start_date: str, end_date: str) -> dict:
        sid = _effective_store_id(tenant_id, store_id)
        return {"storeId": sid, "startDate": start_date, "endDate": end_date}

    async def get_crm_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        params = self._store_aware_params(tenant_id, store_id, start_date, end_date)
        headers = {"Authorization": auth_token} if auth_token else None

        clients_data, contracts_data, follows_data = await asyncio.gather(
            self._http.get("/client-record/statistics", params=params, headers=headers),
            self._http.get("/sales-contract/statistics", params=params, headers=headers),
            self._http.get("/examine-initiate/follow-stats", params=params, headers=headers),
        )

        total_clients = self._num(clients_data.get("total"), 0)
        signed_clients = self._num(contracts_data.get("signedCount"), 0)
        lead_conversion_rate = (signed_clients / total_clients * 100) if total_clients > 0 else 0

        follow_total = self._num(follows_data.get("followTotal"), 0)
        response_time_avg = self._num(follows_data.get("avgResponseHours"), 0)

        return {
            "tenant_id": tenant_id,
            "dimension": "crm",
            "period": f"{start_date} ~ {end_date}",
            "indicators": {
                "lead_conversion_rate": {
                    "value": round(lead_conversion_rate, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"total_clients": total_clients, "signed_clients": signed_clients},
                },
                "response_time_avg": {
                    "value": round(response_time_avg, 2),
                    "unit": "小时",
                    "direction": "lower_is_better",
                    "raw_data": {"avg_response_hours": response_time_avg},
                },
                "follow_up_count": {
                    "value": round(follow_total, 2),
                    "unit": "次",
                    "direction": "higher_is_better",
                    "raw_data": {"follow_total": follow_total},
                },
            },
        }

    async def get_marketing_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        params = self._store_aware_params(tenant_id, store_id, start_date, end_date)
        headers = {"Authorization": auth_token} if auth_token else None

        coupon_data, order_data, exposure_data, seckill_data = await asyncio.gather(
            self._http.get("/account-coupon/statistics", params=params, headers=headers),
            self._http.get("/store-order/conversion-stats", params=params, headers=headers),
            self._http.get("/manage-data/exposure-stats", params=params, headers=headers),
            self._http.get("/seckill-apply/conversion-stats", params=params, headers=headers),
        )

        total_coupons = self._num(coupon_data.get("totalIssued"), 0)
        used_coupons = self._num(coupon_data.get("totalUsed"), 0)
        coupon_rate = (used_coupons / total_coupons * 100) if total_coupons > 0 else 0

        browse_users = self._num(exposure_data.get("browseUsers"), 0)
        order_users = self._num(order_data.get("orderUsers"), 0)
        browse_to_order = (order_users / browse_users * 100) if browse_users > 0 else 0

        total_orders = self._num(order_data.get("totalOrders"), 0)
        completed_orders = self._num(order_data.get("completedOrders"), 0)
        order_conversion = (completed_orders / total_orders * 100) if total_orders > 0 else 0

        seckill_total = self._num(seckill_data.get("totalSeckillGoods"), 0)
        seckill_sold = self._num(seckill_data.get("soldGoods"), 0)
        seckill_rate = (seckill_sold / seckill_total * 100) if seckill_total > 0 else 0

        return {
            "tenant_id": tenant_id,
            "dimension": "marketing",
            "period": f"{start_date} ~ {end_date}",
            "indicators": {
                "coupon_redemption_rate": {
                    "value": round(coupon_rate, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"total_issued": total_coupons, "total_used": used_coupons},
                },
                "browse_to_order_rate": {
                    "value": round(browse_to_order, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"browse_users": browse_users, "order_users": order_users},
                },
                "order_conversion_rate": {
                    "value": round(order_conversion, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"total_orders": total_orders, "completed_orders": completed_orders},
                },
                "seckill_conversion_rate": {
                    "value": round(seckill_rate, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"total_seckill_goods": seckill_total, "sold_goods": seckill_sold},
                },
            },
        }

    async def get_retention_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        params = self._store_aware_params(tenant_id, store_id, start_date, end_date)
        headers = {"Authorization": auth_token} if auth_token else None

        repurchase_data, refund_data, evaluate_data = await asyncio.gather(
            self._http.get("/store-order/repurchase-stats", params=params, headers=headers),
            self._http.get("/store-refund-order/statistics", params=params, headers=headers),
            self._http.get("/store-order-evaluate/statistics", params=params, headers=headers),
        )

        total_buyers = self._num(repurchase_data.get("totalBuyers"), 0)
        repeat_buyers = self._num(repurchase_data.get("repeatBuyers"), 0)
        repurchase_rate = (repeat_buyers / total_buyers * 100) if total_buyers > 0 else 0

        total_completed = self._num(refund_data.get("totalCompletedOrders"), 0)
        refund_orders = self._num(refund_data.get("refundOrders"), 0)
        refund_rate = (refund_orders / total_completed * 100) if total_completed > 0 else 0

        active_customers = self._num(repurchase_data.get("activeCustomers"), 0)
        churned = self._num(repurchase_data.get("churnedCustomers"), 0)
        churn_rate = (churned / active_customers * 100) if active_customers > 0 else 0

        total_reviews = self._num(evaluate_data.get("totalReviews"), 0)
        positive_reviews = self._num(evaluate_data.get("positiveReviews"), 0)
        positive_rate = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0

        avg_ltv = self._num(repurchase_data.get("avgLifetimeValue"), 0)

        return {
            "tenant_id": tenant_id,
            "dimension": "retention",
            "period": f"{start_date} ~ {end_date}",
            "indicators": {
                "repurchase_rate": {
                    "value": round(repurchase_rate, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"total_buyers": total_buyers, "repeat_buyers": repeat_buyers},
                },
                "refund_rate": {
                    "value": round(refund_rate, 2),
                    "unit": "%",
                    "direction": "lower_is_better",
                    "raw_data": {"refund_orders": refund_orders, "total_completed": total_completed},
                },
                "churn_rate": {
                    "value": round(churn_rate, 2),
                    "unit": "%",
                    "direction": "lower_is_better",
                    "raw_data": {"churned": churned, "active_customers": active_customers},
                },
                "positive_review_rate": {
                    "value": round(positive_rate, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"positive_reviews": positive_reviews, "total_reviews": total_reviews},
                },
                "avg_customer_lifetime_value": {
                    "value": round(avg_ltv, 2),
                    "unit": "元",
                    "direction": "higher_is_better",
                    "raw_data": {"avg_ltv": avg_ltv},
                },
            },
        }

    async def get_efficiency_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        params = self._store_aware_params(tenant_id, store_id, start_date, end_date)
        headers = {"Authorization": auth_token} if auth_token else None

        service_data, shipping_data = await asyncio.gather(
            self._http.get("/service-order/completion-stats", params=params, headers=headers),
            self._http.get("/store-order/shipping-stats", params=params, headers=headers),
        )

        total_service = self._num(service_data.get("totalServiceOrders"), 0)
        completed_service = self._num(service_data.get("completedOrders"), 0)
        service_rate = (completed_service / total_service * 100) if total_service > 0 else 0

        avg_shipping = self._num(shipping_data.get("avgShippingHours"), 0)

        return {
            "tenant_id": tenant_id,
            "dimension": "efficiency",
            "period": f"{start_date} ~ {end_date}",
            "indicators": {
                "service_completion_rate": {
                    "value": round(service_rate, 2),
                    "unit": "%",
                    "direction": "higher_is_better",
                    "raw_data": {"total_service": total_service, "completed": completed_service},
                },
                "avg_shipping_hours": {
                    "value": round(avg_shipping, 2),
                    "unit": "小时",
                    "direction": "lower_is_better",
                    "raw_data": {"avg_shipping_hours": avg_shipping},
                },
            },
        }

    async def drill_down_indicator(
        self,
        tenant_id: str,
        store_id: str,
        indicator_code: str,
        start_date: str,
        end_date: str,
        page: int = 1,
        page_size: int = 20,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.core.calculator import DRILL_FIELD_LABELS, DRILL_ITEM_FIELDS, filter_drill_row_by_allowed_fields

        await self._ensure()
        sid = _effective_store_id(tenant_id, store_id)
        params = {
            "storeId": sid,
            "startDate": start_date,
            "endDate": end_date,
            "pageNo": page,
            "pageSize": page_size,
        }
        headers = {"Authorization": auth_token} if auth_token else None

        drill_map = {
            "lead_conversion_rate": ("/client-record/list", {"filterType": "low_conversion"}),
            "response_time_avg": ("/examine-initiate/follow-stats", {"filterType": "slow_response"}),
            "follow_up_count": ("/examine-initiate/follow-stats", {"detail": "true"}),
            "coupon_redemption_rate": ("/account-coupon/statistics", {"filterType": "unused"}),
            "browse_to_order_rate": ("/manage-data/exposure-stats", {"detail": "true"}),
            "order_conversion_rate": ("/store-order/conversion-stats", {"detail": "true"}),
            "seckill_conversion_rate": ("/seckill-apply/conversion-stats", {"detail": "true"}),
            "repurchase_rate": ("/client-record/list", {"filterType": "no_repurchase"}),
            "refund_rate": ("/store-refund-order/statistics", {"detail": "true"}),
            "churn_rate": ("/client-record/list", {"filterType": "churn_risk"}),
            "positive_review_rate": ("/store-order-evaluate/statistics", {"filterType": "negative"}),
            "avg_customer_lifetime_value": ("/store-order/repurchase-stats", {"detail": "true"}),
            "service_completion_rate": ("/service-order/completion-stats", {"detail": "true"}),
            "avg_shipping_hours": ("/store-order/shipping-stats", {"detail": "true"}),
        }

        if indicator_code not in drill_map:
            return {"indicator_code": indicator_code, "total": 0, "items": [], "summary": "该指标暂不支持钻取"}

        endpoint, extra_params = drill_map[indicator_code]
        params.update(extra_params)

        data = await self._http.get(endpoint, params=params, headers=headers)
        raw_items = data.get("list", data.get("items", []))
        allowed = DRILL_ITEM_FIELDS.get(indicator_code)
        items = [filter_drill_row_by_allowed_fields(it, allowed) for it in raw_items] if allowed else raw_items
        field_labels = {k: DRILL_FIELD_LABELS.get(k, k) for k in (allowed or [])}
        return {
            "indicator_code": indicator_code,
            "total": data.get("total", 0),
            "items": items,
            "field_labels": field_labels,
            "summary": data.get("summary", f"{indicator_code} 钻取数据"),
        }
    
    async def send_diagnosis_report_notification(
        self,
        tenant_id: str,
        store_id: str = "",
        admin_account_ids: list | None = None,
        report_summary: dict | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        report_summary = report_summary or {}
        admin_account_ids = admin_account_ids or []

        health_score = report_summary.get("health_score", 0)
        anomaly_count = report_summary.get("anomaly_count", 0)
        top_anomaly = report_summary.get("top_anomaly", "")
        notify_type = report_summary.get("notification_type", "diag_reports")
        diagnosis_time = report_summary.get("diagnosis_time", "")
        analysis_period = report_summary.get("analysis_period_days", 30)

        is_weekly = notify_type == "ai_weekly_digest"
        title = f"{'【周度】' if is_weekly else ''}AI诊断报告已生成 — 健康度 {health_score:.1f}分"
        content = f"诊断时间: {diagnosis_time} | 近{analysis_period}天 | 共发现 {anomaly_count} 项异常指标。"
        if top_anomaly:
            content += f"最突出问题：{top_anomaly}。"
        content += "详情请到APP/后台查看"

        messages = [
            {
                "accountId": aid,
                "title": title,
                "content": content,
                "type": notify_type,
                "jumpUrl": report_summary.get("report_url", ""),
            }
            for aid in admin_account_ids
        ]

        if not messages:
            return {"sent_count": 0, "status": "no_admin"}

        data = await self._http.post("/message-remind/batch-create", json_data={"messages": messages})
        return {"sent_count": len(messages), "status": "sent", **data}

    async def send_task_reminder(
        self,
        tenant_id: str,
        user_id: int = 0,
        account_id: str = "",
        task_id: str = "",
        reminder_type: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        await self._ensure()
        type_labels = {
            "overdue": "任务超期提醒",
            "approaching_deadline": "任务即将到期",
            "blocked": "任务受阻提醒",
        }
        title = type_labels.get(reminder_type, "任务提醒")

        data = await self._http.post(
            "/message-remind/batch-create",
            json_data={
                "messages": [
                    {
                        "accountId": account_id,
                        "title": title,
                        "content": message,
                        "type": f"ai_task_{reminder_type}",
                        "bizId": task_id,
                    }
                ],
            },
        )
        return {"status": "sent", **data}

    async def send_plan_adoption_request(
        self,
        tenant_id: str,
        store_id: str = "",
        admin_account_ids: list | None = None,
        thread_id: str = "",
        plans_summary: list | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        admin_account_ids = admin_account_ids or []
        plans_summary = plans_summary or []

        plan_names = "、".join(p.get("name", "") for p in plans_summary[:3])
        title = f"您有 {len(plans_summary)} 个 AI 优化方案待审阅采纳"
        content = f"AI 已基于当前业务数据，为您生成了 {len(plans_summary)} 份针对性优化方案（{plan_names}）。方案详情已准备就绪，请前往 【企业APP → AI智能诊断 → 推荐方案】 尽快查看并选择采纳，以便及时落地执行。"

        messages = [
            {
                "accountId": aid,
                "title": title,
                "content": content,
                "type": "ai_plan_adoption",
                "jumpUrl": thread_id,
            }
            for aid in admin_account_ids
        ]

        if not messages:
            return {"sent_count": 0, "status": "no_admin"}

        data = await self._http.post("/message-remind/batch-create", json_data={"messages": messages})
        return {"sent_count": len(messages), "status": "sent", **data}

    async def send_review_report_notification(
        self,
        tenant_id: str,
        store_id: str = "",
        admin_account_ids: list | None = None,
        thread_id: str = "",
        review_summary: dict | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        admin_account_ids = admin_account_ids or []
        review_summary = review_summary or {}

        achievement = review_summary.get("overall_achievement", 0)
        improved = review_summary.get("improved_count", 0)
        total = review_summary.get("total_indicators", 0)
        solution_name = review_summary.get("solution_name", "")
        report_time = review_summary.get("report_time", "")
        tracking_period = review_summary.get("tracking_period", "")

        parts = []
        if solution_name:
            parts.append(f"方案: {solution_name}")
        if tracking_period:
            parts.append(f"追踪区间: {tracking_period}")
        parts.append(f"达成率 {achievement:.0f}%（{improved}/{total} 项指标改善）")
        if report_time:
            parts.append(f"报告时间: {report_time}")
        parts.append("报告详情请到【APP → AI智能诊断 → 效果追踪】中查看")

        title = f"方案复盘完成 — 达成率 {achievement:.0f}%"
        content = " | ".join(parts)

        messages = [
            {
                "accountId": aid,
                "title": title,
                "content": content,
                "type": "review_reports",
                "jumpUrl": thread_id,
            }
            for aid in admin_account_ids
        ]

        if not messages:
            return {"sent_count": 0, "status": "no_admin"}

        data = await self._http.post("/message-remind/batch-create", json_data={"messages": messages})
        return {"sent_count": len(messages), "status": "sent", **data}

    async def send_task_assignment_notification(
        self,
        tenant_id: str,
        store_id: str = "",
        tasks: list | None = None,
    ) -> dict[str, Any]:
        await self._ensure()
        tasks = tasks or []

        messages = []
        for t in tasks:
            account_id = t.get("assignee_account_id") or t.get("assignee_user_id")
            if not account_id:
                continue
            task_name = t.get("task_name", "")
            deadline = t.get("deadline", "")
            messages.append(
                {
                    "accountId": str(account_id),
                    "title": f"新任务分配：{task_name}",
                    "content": f"您有一项新的AI诊断执行任务「{task_name}」，请在{deadline}前完成。",
                    "type": "ai_task_assignment",
                    "bizId": t.get("task_id", ""),
                }
            )

        if not messages:
            return {"sent_count": 0, "status": "no_assignee"}

        data = await self._http.post("/message-remind/batch-create", json_data={"messages": messages})
        return {"sent_count": len(messages), "status": "sent", **data}

    async def send_customer_targeted_message(
        self,
        tenant_id: str,
        store_id: str = "",
        target_segment: str = "",
        title: str = "",
        content: str = "",
        message_type: str = "ai_targeted",
    ) -> dict[str, Any]:
        await self._ensure()
        sid = _effective_store_id(tenant_id, store_id)
        body = {
            "storeId": sid,
            "targetSegment": target_segment,
            "title": title,
            "content": content,
            "type": message_type,
        }
        data = await self._http.post("/message-remind/targeted", json_data=body)
        return {"sent_count": data.get("sent_count", 0), "status": "sent", **data}
