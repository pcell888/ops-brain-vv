"""应用根日志：控制台 + 滚动文件。"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from src.core.config import get_settings

# 与 MCP 子进程共用，避免重复挂载 handler
_BIZ_API_MCP_MIRROR_KEY = "_ops_brain_mcp_servers_mirror"


def _attach_biz_api_to_mcp_servers_log(log_dir: Path, fmt: logging.Formatter) -> None:
    """将业务 API 客户端日志镜像到 mcp-servers.log（诊断钻取等与 MCP 工具同源排查）。"""
    mcp_path = log_dir / "mcp-servers.log"
    biz = logging.getLogger("src.mcp_servers.biz_api_client")
    for h in biz.handlers:
        if getattr(h, _BIZ_API_MCP_MIRROR_KEY, False):
            return
    fh = logging.handlers.RotatingFileHandler(
        mcp_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    setattr(fh, _BIZ_API_MCP_MIRROR_KEY, True)
    biz.addHandler(fh)
    # 镜像 DEBUG（如响应体摘要）；根 logger 仍为 INFO 时不在控制台刷屏
    biz.setLevel(logging.DEBUG)


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

    _attach_biz_api_to_mcp_servers_log(log_dir, fmt)
