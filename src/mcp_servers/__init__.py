"""MCP Servers 日志配置。"""

import logging
import logging.handlers
import sys
from pathlib import Path

from src.core.config import get_settings

# 获取日志配置
settings = get_settings()
log_dir = Path(settings.log_dir)
log_dir.mkdir(parents=True, exist_ok=True)

# 为 MCP Server 配置日志输出到 stderr（避免干扰 stdio 通信）
_handler = logging.StreamHandler(sys.stderr)
_handler.setLevel(logging.DEBUG)
_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
_handler.setFormatter(_formatter)

# 配置文件日志
_file_handler = logging.handlers.RotatingFileHandler(
    log_dir / "mcp-servers.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_formatter)

# 配置根日志器
logging.getLogger().addHandler(_handler)
logging.getLogger().addHandler(_file_handler)
logging.getLogger().setLevel(logging.DEBUG)

logging.getLogger("mcp_servers.bootstrap").info(
    "MCP 子进程已初始化 log_dir=%s（mcp-servers.log）",
    log_dir.resolve(),
)
