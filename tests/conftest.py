"""pytest 公共 fixture：mock DB 后提供 wlwq 应用与 TestClient。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.wlwq.app import app


@pytest.fixture
def client() -> TestClient:
    with patch("src.wlwq.database.get_pool", new_callable=AsyncMock) as mock_get:
        with patch("src.wlwq.database.close_pool", new_callable=AsyncMock):
            mock_get.return_value = None
            with TestClient(app) as c:
                yield c
