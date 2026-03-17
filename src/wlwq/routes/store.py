"""店铺与行业分类 — 供 MCP crm-server get_store_profile 调用。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["store"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/store/list")
async def list_stores():
    """企业下所有店铺列表（全企业诊断用）。"""
    return _ok({
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
    })


@router.get("/store/{store_id}")
async def get_store(store_id: str):
    """店铺画像，get_store_profile 用。"""
    return _ok({
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
    })


@router.get("/store-class/{class_id}")
async def get_store_class(class_id: str):
    """行业分类，get_store_profile 用。"""
    return _ok({
        "classCode": "retail_general",
        "className": "综合零售",
    })
