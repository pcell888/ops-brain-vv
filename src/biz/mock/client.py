"""本地业务模拟 — 复用现有 biz/mock 的 dispatcher"""

from __future__ import annotations

from typing import Any

from src.biz.tenant_client import TenantClient


async def _dispatch(method: str, path: str, params: dict | None = None, json_data: dict | None = None) -> dict[str, Any]:
    from src.biz.mock.dispatch import dispatch_biz_mock
    return await dispatch_biz_mock(method, path, params or {}, json_data or {})


class MockTenantClient(TenantClient):
    """本地业务模拟 — 复用现有 biz/mock 的 dispatcher"""

    async def get_store_profile(self, tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        sid = effective_store_id_for_biz(tenant_id, store_id)
        if not sid:
            store_list = await _dispatch("GET", "store/list")
            return {
                "tenant_id": tenant_id,
                "store_id": "",
                "store_name": f"{tenant_id}（全企业）",
                "store_type": "enterprise",
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
                "scope": "enterprise",
                "stores": [{"store_id": s.get("storeId"), "store_name": s.get("storeName")} for s in store_list.get("list", [])],
            }
        store_data = await _dispatch("GET", f"store/{sid}")
        class_id = store_data.get("classId")
        class_data = {}
        if class_id:
            class_data = await _dispatch("GET", f"store-class/{class_id}")
        return {
            "tenant_id": tenant_id,
            "store_id": sid,
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

    async def get_customer_list(
        self,
        tenant_id: str,
        store_id: str = "",
        filter_type: str = "all",
        page: int = 1,
        page_size: int = 20,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        sid = effective_store_id_for_biz(tenant_id, store_id)
        params = {"storeId": sid, "filterType": filter_type, "pageNo": page, "pageSize": page_size}
        data = await _dispatch("GET", "client-record/list", params)
        return {"total": data.get("total", 0), "items": data.get("list", [])}

    async def get_customer_detail(self, tenant_id: str, client_record_id: str, auth_token: str | None = None) -> dict[str, Any]:
        client_data = await _dispatch("GET", f"client-record/{client_record_id}")
        contracts = await _dispatch("GET", "sales-contract/list", {"clientRecordId": client_record_id})
        client_data["contracts"] = contracts.get("list", [])
        return client_data

    async def get_sales_contract_list(
        self,
        tenant_id: str,
        client_record_id: str | None = None,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        params = {"clientRecordId": client_record_id} if client_record_id else {}
        data = await _dispatch("GET", "sales-contract/list", params)
        return {"total": data.get("total", 0), "items": data.get("list", [])}

    async def get_order_analytics(
        self,
        tenant_id: str,
        store_id: str = "",
        start_date: str = "",
        end_date: str = "",
        group_by: str = "day",
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        sid = effective_store_id_for_biz(tenant_id, store_id)
        params = {"storeId": sid, "startDate": start_date, "endDate": end_date, "groupBy": group_by}
        return await _dispatch("GET", "store-order/analytics", params)

    async def get_dept_tree(self, tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        sid = effective_store_id_for_biz(tenant_id, store_id)
        return await _dispatch("GET", "sys-dept/tree", {"storeId": sid})

    async def get_users_by_dept(self, tenant_id: str, dept_id: str, auth_token: str | None = None) -> dict[str, Any]:
        data = await _dispatch("GET", "sys-user/list", {"deptId": dept_id})
        return {"list": data.get("list", [])}

    async def get_dept_structure(self, tenant_id: str, store_id: str = "", auth_token: str | None = None) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        sid = effective_store_id_for_biz(tenant_id, store_id)
        if sid:
            return await self._fetch_dept_tree_mock(sid)
        store_list = await _dispatch("GET", "store/list")
        stores = store_list.get("list", [])
        if not stores:
            return {"store_id": "", "departments": []}
        trees = [await self._fetch_dept_tree_mock(s.get("storeId", "")) for s in stores]
        seen_ids: set = set()
        merged: list[dict] = []
        for tree in trees:
            for dept in tree.get("departments", []):
                did = dept.get("dept_id")
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    merged.append(dept)
        return {"store_id": "", "departments": merged}

    async def _fetch_dept_tree_mock(self, store_id: str) -> dict:
        dept_tree = await _dispatch("GET", "sys-dept/tree", {"storeId": store_id})
        raw_list = dept_tree.get("list") or dept_tree.get("children") or []
        departments = []
        for dept in raw_list:
            dept_id = dept.get("deptId", dept.get("id"))
            users_data = await _dispatch("GET", "sys-user/list", {"deptId": dept_id})
            users = users_data.get("list") or []
            departments.append({
                "dept_id": dept_id,
                "dept_name": dept.get("deptName", dept.get("name", "")),
                "parent_id": dept.get("parentId"),
                "users": users,
            })
        return {"store_id": store_id, "departments": departments}

    async def create_execution_tasks(self, tenant_id: str, store_id: str = "", plan_id: str = "", tasks: list | None = None) -> dict[str, Any]:
        payload = {"storeId": store_id, "planId": plan_id, "tasks": tasks or []}
        data = await _dispatch("POST", "ai-diagnosis/exec-task/batch-create", json_data=payload)
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
        data = await _dispatch("GET", "ai-diagnosis/hasCreateTaskPermission", {"userId": user_id})
        raw = data.get("hasPermission", data.get("has_permission", data.get("data", data)))
        if isinstance(raw, str):
            has_permission = raw.strip().lower() == "true"
        else:
            has_permission = bool(raw)
        return {"has_permission": has_permission}

    async def create_approval_flow(
        self,
        tenant_id: str,
        store_id: str = "",
        plan_id: str = "",
        title: str = "",
        content: str = "",
        approver_user_id: int = 0,
    ) -> dict[str, Any]:
        payload = {
            "storeId": store_id,
            "title": title,
            "content": content,
            "approverUserId": approver_user_id,
            "bizType": "ai_diagnosis",
            "bizId": plan_id,
        }
        data = await _dispatch("POST", "examine-initiate/create", json_data=payload)
        return {"approval_id": data.get("id", ""), "status": "pending"}

    async def update_task_status(
        self,
        tenant_id: str,
        task_id: str = "",
        status: str = "",
        progress: float | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        payload: dict = {"status": status}
        if progress is not None:
            payload["progress"] = progress
        if remark:
            payload["remark"] = remark
        data = await _dispatch("PUT", f"ai-diagnosis/exec-task/{task_id}/status", json_data=payload)
        return {"task_id": task_id, "status": status, "updated": True, **data}

    async def create_coupon_campaign(
        self,
        tenant_id: str,
        store_id: str = "",
        campaign_config: dict | None = None,
    ) -> dict[str, Any]:
        config = campaign_config or {}
        create_body = {
            "storeId": store_id,
            "couponName": config.get("coupon_name"),
            "couponType": config.get("coupon_type", 1),
            "startTime": config.get("start_time"),
            "endTime": config.get("end_time"),
        }
        coupon_data = await _dispatch("POST", "coupon/create", json_data=create_body)
        coupon_id = coupon_data.get("id") or coupon_data.get("couponId", "")
        dist_body = {"storeId": store_id, "couponId": coupon_id, "targetCustomers": config.get("target_customers", "all")}
        distribute_data = await _dispatch("POST", "coupon/distribute", json_data=dist_body)
        return {"coupon_id": coupon_id, "distributed_count": distribute_data.get("count", 0), "campaign_config": config}

    async def create_seckill_activity(
        self,
        tenant_id: str,
        store_id: str = "",
        activity_config: dict | None = None,
    ) -> dict[str, Any]:
        body = dict(activity_config or {})
        body["storeId"] = store_id
        data = await _dispatch("POST", "seckill-apply/create", json_data=body)
        return {"activity_id": data.get("id", ""), "status": "created"}

    async def get_crm_indicators(
        self,
        tenant_id: str,
        store_id: str = "",
        start_date: str = "",
        end_date: str = "",
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        from src.biz.mock.mock_metrics import get_crm_indicators as _mock_get_crm
        sid = effective_store_id_for_biz(tenant_id, store_id)
        return await _mock_get_crm(tenant_id, sid, start_date, end_date, auth_token)

    async def get_marketing_indicators(
        self,
        tenant_id: str,
        store_id: str = "",
        start_date: str = "",
        end_date: str = "",
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        from src.biz.mock.mock_metrics import get_marketing_indicators as _mock_get_marketing
        sid = effective_store_id_for_biz(tenant_id, store_id)
        return await _mock_get_marketing(tenant_id, sid, start_date, end_date, auth_token)

    async def get_retention_indicators(
        self,
        tenant_id: str,
        store_id: str = "",
        start_date: str = "",
        end_date: str = "",
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        from src.biz.mock.mock_metrics import get_retention_indicators as _mock_get_retention
        sid = effective_store_id_for_biz(tenant_id, store_id)
        return await _mock_get_retention(tenant_id, sid, start_date, end_date, auth_token)

    async def get_efficiency_indicators(
        self,
        tenant_id: str,
        store_id: str = "",
        start_date: str = "",
        end_date: str = "",
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        from src.biz.mock.mock_metrics import get_efficiency_indicators as _mock_get_efficiency
        sid = effective_store_id_for_biz(tenant_id, store_id)
        return await _mock_get_efficiency(tenant_id, sid, start_date, end_date, auth_token)

    async def drill_down_indicator(
        self,
        tenant_id: str,
        store_id: str = "",
        indicator_code: str = "",
        start_date: str = "",
        end_date: str = "",
        page: int = 1,
        page_size: int = 20,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        from src.biz.biz_scope import effective_store_id_for_biz
        from src.biz.mock.mock_metrics import drill_down_indicator as _mock_drill_down
        sid = effective_store_id_for_biz(tenant_id, store_id)
        return await _mock_drill_down(tenant_id, sid, indicator_code, start_date, end_date, page, page_size, auth_token)

    async def send_diagnosis_report_notification(
        self,
        tenant_id: str,
        store_id: str = "",
        admin_account_ids: list | None = None,
        report_summary: dict | None = None,
    ) -> dict[str, Any]:
        from src.biz.mock.mock_notify import send_diagnosis_report_notification as _mock_notify
        return await _mock_notify(tenant_id, store_id, admin_account_ids or [], report_summary or {})

    async def send_task_reminder(
        self,
        tenant_id: str,
        user_id: int = 0,
        account_id: str = "",
        task_id: str = "",
        reminder_type: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        from src.biz.mock.mock_notify import send_task_reminder as _mock_reminder
        return await _mock_reminder(tenant_id, user_id, account_id, task_id, reminder_type, message)

    async def send_plan_adoption_request(
        self,
        tenant_id: str,
        store_id: str = "",
        admin_account_ids: list | None = None,
        thread_id: str = "",
        plans_summary: list | None = None,
    ) -> dict[str, Any]:
        from src.biz.mock.mock_notify import send_plan_adoption_request as _mock_adoption
        return await _mock_adoption(tenant_id, store_id, admin_account_ids or [], thread_id, plans_summary or [])

    async def send_review_report_notification(
        self,
        tenant_id: str,
        store_id: str = "",
        admin_account_ids: list | None = None,
        thread_id: str = "",
        review_summary: dict | None = None,
    ) -> dict[str, Any]:
        from src.biz.mock.mock_notify import send_review_report_notification as _mock_review
        return await _mock_review(tenant_id, store_id, admin_account_ids or [], thread_id, review_summary or {})

    async def send_task_assignment_notification(
        self,
        tenant_id: str,
        store_id: str = "",
        tasks: list | None = None,
    ) -> dict[str, Any]:
        from src.biz.mock.mock_notify import send_task_assignment_notification as _mock_assign
        return await _mock_assign(tenant_id, store_id, tasks or [])

    async def send_customer_targeted_message(
        self,
        tenant_id: str,
        store_id: str = "",
        target_segment: str = "",
        title: str = "",
        content: str = "",
        message_type: str = "ai_targeted",
    ) -> dict[str, Any]:
        from src.biz.mock.mock_notify import send_customer_targeted_message as _mock_targeted
        return await _mock_targeted(tenant_id, store_id, target_segment, title, content, message_type)
