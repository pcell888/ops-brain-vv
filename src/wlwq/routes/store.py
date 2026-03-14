"""店铺与行业分类 — 供 MCP crm-server get_store_profile 调用。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["store"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/store/{store_id}")
async def get_store(store_id: str):
    """店铺画像，get_store_profile 用。"""
    return _ok({
        "storeName": "AI示范店",
        "storeType": "retail",
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
    })


@router.get("/store-class/{class_id}")
async def get_store_class(class_id: str):
    """行业分类，get_store_profile 用。"""
    return _ok({
        "classCode": "retail_general",
        "className": "综合零售",
    })
