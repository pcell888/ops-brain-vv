"""业务 API 抽象 — 定义所有业务方法的输入输出契约"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TenantClient(ABC):
    """业务 API 抽象基类"""
    
    async def get_store_profile(
        self, tenant_id: str, store_id: str = "", auth_token: str | None = None
    ) -> dict[str, Any]:
        ...

    async def get_customer_list(
        self,
        tenant_id: str,
        store_id: str,
        filter_type: str = "all",
        page: int = 1,
        page_size: int = 20,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def get_customer_detail(
        self, tenant_id: str, client_record_id: str, auth_token: str | None = None
    ) -> dict[str, Any]:
        ...

    async def get_sales_contract_list(
        self, tenant_id: str, client_record_id: str | None = None, auth_token: str | None = None
    ) -> dict[str, Any]:
        ...

    async def get_order_analytics(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        group_by: str = "day",
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def get_dept_tree(
        self, tenant_id: str, store_id: str = "", auth_token: str | None = None
    ) -> dict[str, Any]:
        ...

    async def get_users_by_dept(
        self, tenant_id: str, dept_id: str, auth_token: str | None = None
    ) -> dict[str, Any]:
        ...

    async def get_dept_structure(
        self, tenant_id: str, store_id: str = "", auth_token: str | None = None
    ) -> dict[str, Any]:
        ...

    async def create_execution_tasks(
        self, tenant_id: str, store_id: str, plan_id: str, tasks: list[dict]
    ) -> dict[str, Any]:
        ...

    async def has_create_task_permission(
        self,
        tenant_id: str,
        user_id: int,
    ) -> dict[str, Any]:
        ...

    async def create_approval_flow(
        self,
        tenant_id: str,
        store_id: str,
        plan_id: str,
        title: str,
        content: str,
        approver_user_id: int,
    ) -> dict[str, Any]:
        ...

    async def update_task_status(
        self,
        tenant_id: str,
        task_id: str,
        status: str,
        progress: float | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def create_coupon_campaign(
        self, tenant_id: str, store_id: str, campaign_config: dict
    ) -> dict[str, Any]:
        ...

    async def create_seckill_activity(
        self, tenant_id: str, store_id: str, activity_config: dict
    ) -> dict[str, Any]:
        ...

    async def get_crm_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def get_marketing_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def get_retention_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        ...

    async def get_efficiency_indicators(
        self,
        tenant_id: str,
        store_id: str,
        start_date: str,
        end_date: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        ...

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
        ...

    async def send_diagnosis_report_notification(
        self,
        tenant_id: str,
        store_id: str,
        admin_account_ids: list[str],
        report_summary: dict,
    ) -> dict[str, Any]:
        ...

    async def send_task_reminder(
        self,
        tenant_id: str,
        user_id: int,
        account_id: str,
        task_id: str,
        reminder_type: str,
        message: str,
    ) -> dict[str, Any]:
        ...

    async def send_plan_adoption_request(
        self,
        tenant_id: str,
        store_id: str,
        admin_account_ids: list[str],
        thread_id: str,
        plans_summary: list[dict],
    ) -> dict[str, Any]:
        ...

    async def send_review_report_notification(
        self,
        tenant_id: str,
        store_id: str,
        admin_account_ids: list[str],
        thread_id: str,
        review_summary: dict,
    ) -> dict[str, Any]:
        ...

    async def send_task_assignment_notification(
        self, tenant_id: str, store_id: str, tasks: list[dict]
    ) -> dict[str, Any]:
        ...

    async def send_customer_targeted_message(
        self,
        tenant_id: str,
        store_id: str,
        target_segment: str,
        title: str,
        content: str,
        message_type: str = "ai_targeted",
    ) -> dict[str, Any]:
        ...
