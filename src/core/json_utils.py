"""JSON 解析工具 — 统一 llm_caller 与 agent/tools 的实现。"""

from __future__ import annotations

import json
from typing import Any


def strip_json_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_json_fence(text: str) -> Any | None:
    body = strip_json_fence(text)
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None
