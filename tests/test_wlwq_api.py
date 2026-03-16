"""wlwq FastAPI 接口 — 健康检查与 exec-task 占位。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(client: TestClient) -> TestClient:
    return client


def test_health(api_client: TestClient):
    r = api_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "service" in data


def test_exec_task_batch_create(api_client: TestClient):
    body = {
        "storeId": "store_1",
        "planId": "rule_5.2.3",
        "tasks": [
            {"task_name": "线索跟进优化", "owner_dept": "销售", "timeline": "24小时内"},
        ],
    }
    r = api_client.post("/ai-diagnosis/exec-task/batch-create", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data.get("code") == 0
    inner = data.get("data", {})
    assert "tasks" in inner and "count" in inner
    assert inner["count"] == 1
    assert inner["tasks"][0].get("task_name") == "线索跟进优化"
    assert "task_id" in inner["tasks"][0]


def test_exec_task_update_status(api_client: TestClient):
    r = api_client.put(
        "/ai-diagnosis/exec-task/task_0/status",
        json={"status": "completed", "progress": 100},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("code") == 0
    assert data.get("data", {}).get("task_id") == "task_0"
    assert data.get("data", {}).get("updated") is True


def test_message_remind_targeted(api_client: TestClient):
    body = {
        "storeId": "store_1",
        "targetSegment": "churn_risk",
        "title": "专属关怀",
        "content": "感谢支持",
        "type": "churn_care",
    }
    r = api_client.post("/message-remind/targeted", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data.get("code") == 0
    assert "sent_count" in data.get("data", {})
