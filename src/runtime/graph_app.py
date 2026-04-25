"""公共工具 — generate_thread_id。"""

from __future__ import annotations

import uuid
from datetime import datetime

from src.core.config import CN_TZ


def generate_thread_id() -> str:
    return f"diag_{datetime.now(CN_TZ).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
