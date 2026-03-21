"""应用根日志：控制台 + 滚动文件。"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from src.core.config import get_settings


def setup_logging(file_stem: str) -> None:
    s = get_settings()
    level = getattr(logging, s.log_level.upper(), logging.INFO)
    log_dir = Path(s.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{file_stem}.log"

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    fh = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)
