"""客户记录、合同、审批跟进 — 原 wlwq client_record / sales_contract / examine_initiate。"""

from __future__ import annotations

import random as _r
import uuid

from src.mcp_servers.biz_mock.random_util import (
    query_param_bool,
    random_enabled,
    random_float,
    random_int,
    use_random_from_params,
)


def _mock_client_list(page_size: int) -> tuple[list[dict], int]:
    total = 127
    rows = []
    for i in range(min(int(page_size), 5)):
        rows.append(
            {
                "id": f"cr_{uuid.uuid4().hex[:10]}",
                "name": f"模拟客户{i + 1}",
                "phone": f"138****{1000 + i}",
                "tags": ["vip"] if i % 2 == 0 else ["new"],
                "lastOrderDays": 3 + i * 7,
            }
        )
    return rows, total


def client_record_statistics(params: dict) -> dict:
    if random_enabled(use_random_from_params(params)):
        total = random_int("WLWQ_CLIENT_TOTAL_RANDOM_MIN", "WLWQ_CLIENT_TOTAL_RANDOM_MAX", 2600, 3400)
        new_clients = random_int("WLWQ_CLIENT_NEW_RANDOM_MIN", "WLWQ_CLIENT_NEW_RANDOM_MAX", 80, 200)
        return {"total": total, "newClients": new_clients}
    return {"total": 3012, "newClients": 142}


def client_record_list(params: dict) -> dict:
    page_size = int(params.get("pageSize") or 20)
    current_page = int(params.get("pageNo") or params.get("page") or 1)
    rows, total = _mock_client_list(page_size)
    _ = (params.get("storeId"), params.get("filterType"), current_page)
    return {"list": rows, "total": total}


def client_record_detail(client_record_id: str) -> dict:
    return {
        "id": client_record_id,
        "name": "模拟客户",
        "phone": "138****0000",
        "totalOrders": 12,
        "totalAmount": 18600.50,
    }


def sales_contract_statistics(params: dict) -> dict:
    if random_enabled(use_random_from_params(params)):
        return {
            "signedCount": random_int("WLWQ_SALES_CONTRACT_RANDOM_MIN", "WLWQ_SALES_CONTRACT_RANDOM_MAX", 70, 120),
            "totalAmount": random_float(
                "WLWQ_SALES_AMOUNT_RANDOM_MIN", "WLWQ_SALES_AMOUNT_RANDOM_MAX", 280000.0, 520000.0
            ),
        }
    return {"signedCount": 96, "totalAmount": 412000.0}


def sales_contract_list(params: dict) -> dict:
    page_size = int(params.get("pageSize") or 20)
    current_page = int(params.get("pageNo") or params.get("page") or 1)
    rows = [
        {"id": f"sc_{uuid.uuid4().hex[:10]}", "amount": 12800.0 + i * 1000, "status": 1 + (i % 3)}
        for i in range(min(page_size, 5))
    ]
    _ = (params.get("clientRecordId"), current_page)
    return {"list": rows, "total": 48}


def _gen_ei_id() -> str:
    return f"ei_{uuid.uuid4().hex[:16]}"


def examine_follow_stats(params: dict) -> dict:
    from datetime import datetime, timedelta

    detail = query_param_bool(params, "detail")
    filter_type = params.get("filterType")
    page_size = int(params.get("pageSize") or 20)
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"), int(params.get("page") or 1), page_size)

    if detail or filter_type == "slow_response":
        rows = []
        base_time = datetime.now() - timedelta(days=30)
        for i in range(15):
            t = (base_time + timedelta(days=_r.randint(0, 30), hours=_r.randint(0, 23))).strftime("%Y-%m-%d %H:%M:%S")
            finish = (base_time + timedelta(hours=_r.randint(1, 72))).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(
                {
                    "examine_initiate_id": _gen_ei_id(),
                    "content": _r.choice(["电话跟进", "客户拜访", "方案发送", "需求确认"]),
                    "create_time": t,
                    "finish_time": finish,
                    "user_name": _r.choice(["张三", "李四", "王五", "赵六"]),
                }
            )
        return {"total": len(rows) * 3, "list": rows}

    if random_enabled(use_random_from_params(params)):
        return {
            "followTotal": random_int("WLWQ_FOLLOW_TOTAL_RANDOM_MIN", "WLWQ_FOLLOW_TOTAL_RANDOM_MAX", 380, 720),
            "avgResponseHours": random_float(
                "WLWQ_AVG_RESPONSE_RANDOM_MIN", "WLWQ_AVG_RESPONSE_RANDOM_MAX", 8.0, 12.0, 2
            ),
        }
    return {"followTotal": 520, "avgResponseHours": 9.6}


def examine_turnaround_stats(params: dict) -> dict:
    _ = (params.get("storeId"), params.get("startDate"), params.get("endDate"))
    if random_enabled(use_random_from_params(params)):
        return {
            "onTimeRate": random_float(
                "WLWQ_ON_TIME_RATE_RANDOM_MIN", "WLWQ_ON_TIME_RATE_RANDOM_MAX", 45.0, 68.0, 2
            )
        }
    return {"onTimeRate": 58.5}


def examine_create(body: dict) -> dict:
    approver_user_id = body.get("approverUserId")
    biz_type = body.get("bizType", "")
    biz_id = body.get("bizId", "")
    ei_id = _gen_ei_id()[:20]
    return {
        "id": ei_id,
        "examine_status": 1,
        "approver_user_id": approver_user_id,
        "biz_type": biz_type,
        "biz_id": biz_id,
    }
