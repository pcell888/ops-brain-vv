"""应用根日志：控制台 + 滚动文件，JSON 格式，自动注入 OpenTelemetry trace_id / span_id。"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from pythonjsonlogger import jsonlogger

from src.core.config import get_settings

_BIZ_API_MCP_MIRROR_KEY = "_ops_brain_mcp_servers_mirror"
_REPO_ROOT = Path(__file__).resolve().parents[2]


class TraceIdFilter(logging.Filter):
    """从当前 OpenTelemetry span 中提取 trace_id / span_id 注入到日志记录中。"""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid and ctx.trace_id != 0:
                record.trace_id = f"{ctx.trace_id:032x}"
                record.span_id = f"{ctx.span_id:016x}"
            else:
                record.trace_id = ""
                record.span_id = ""
        except Exception:
            record.trace_id = ""
            record.span_id = ""
        return True


class ExtraContextFilter(logging.Filter):
    """为日志记录注入 tenant_id / thread_id 默认值，避免 JSON 中出现 null。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "tenant_id"):
            record.tenant_id = ""
        if not hasattr(record, "thread_id"):
            record.thread_id = ""
        return True


def _json_formatter() -> jsonlogger.JsonFormatter:
    return jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s %(tenant_id)s %(thread_id)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        json_ensure_ascii=False,
    )


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
    fh.addFilter(TraceIdFilter())
    fh.addFilter(ExtraContextFilter())
    setattr(fh, _BIZ_API_MCP_MIRROR_KEY, True)
    biz.addHandler(fh)
    biz.setLevel(logging.DEBUG)


def setup_logging(file_stem: str, console: bool = True) -> None:
    """初始化日志。MCP 子进程须传 console=False，避免 stderr 干扰 stdio 协议。"""
    s = get_settings()
    level = getattr(logging, s.log_level.upper(), logging.INFO)
    log_dir = Path(s.log_dir)
    if not log_dir.is_absolute():
        log_dir = (_REPO_ROOT / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{file_stem}.log"

    root = logging.getLogger()
    for h in root.handlers[:]:
        try:
            h.flush()
            h.close()
        except Exception:
            pass
        root.removeHandler(h)
    root.setLevel(level)

    fmt = _json_formatter()
    trace_filter = TraceIdFilter()
    extra_filter = ExtraContextFilter()

    if console:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        ch.addFilter(trace_filter)
        ch.addFilter(extra_filter)
        root.addHandler(ch)

    fh = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    fh.addFilter(trace_filter)
    fh.addFilter(extra_filter)
    root.addHandler(fh)

    # 第三方 HTTP 库只保留告警以上，避免请求调试细节污染业务日志。
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _attach_biz_api_to_mcp_servers_log(log_dir, fmt)
    root.info("日志已初始化 | log_path=%s", str(log_path))
