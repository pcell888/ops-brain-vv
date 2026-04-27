"""CRM 原始数据 — 供 dispatch 路由；进程内模拟。"""

from __future__ import annotations

from src.biz.mock.handlers import client_sales_examine
from src.biz.mock.handlers.stats import store_order_analytics


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


def try_raw_request(method: str, path: str, q: dict, body: dict) -> dict | None:
    _ = (method, path, q, body)
    return None