from __future__ import annotations

from src.wlwq.routes.exec_task import _parse_deadline_at


def test_parse_deadline_at_supports_snake_case():
    task = {"deadline_at": "2026-03-31T10:00:00+08:00"}
    dt = _parse_deadline_at(task)
    assert dt is not None
    assert dt.isoformat() == "2026-03-31T10:00:00+08:00"


def test_parse_deadline_at_supports_camel_case():
    task = {"deadlineAt": "2026-03-31T10:00:00+08:00"}
    dt = _parse_deadline_at(task)
    assert dt is not None
    assert dt.isoformat() == "2026-03-31T10:00:00+08:00"
