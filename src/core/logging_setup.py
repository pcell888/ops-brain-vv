"""应用根日志：控制台 + 滚动文件；默认易读文本（年月日 时分秒）。可选 JSON（json_logs=True）；仍注入 trace 等字段供 JSON 使用。"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - depends on runtime env
    jsonlogger = None

from src.core.config import get_settings

_MCP_SERVERS_MIRROR_ATTR = "_ops_brain_mcp_servers_mirror"
_REPO_ROOT = Path(__file__).resolve().parents[2]
# 与 MCP 子进程共用 mcp-servers.log，便于按同一文件排查「HTTP 钻取 + 下游业务 API」。
_MCP_SERVERS_MIRROR_LOGGERS: tuple[str, ...] = (
    "src.mcp_servers.biz_api_client",
    "src.api.routes.drill_down",
    "src.api.routes.compat_diagnosis",
)


class TraceIdFilter(logging.Filter):
    """保留 trace/span 字段，当前未启用分布式追踪时填空字符串。"""

    def filter(self, record: logging.LogRecord) -> bool:
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


def _json_formatter() -> logging.Formatter:
    if jsonlogger is None:
        return _plain_formatter()
    return jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(message)s %(trace_id)s %(span_id)s %(tenant_id)s %(thread_id)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
        },
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        json_ensure_ascii=False,
    )


def _plain_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _remove_mcp_servers_mirror_handlers(lg: logging.Logger) -> None:
    for h in lg.handlers[:]:
        if getattr(h, _MCP_SERVERS_MIRROR_ATTR, False):
            lg.removeHandler(h)
            try:
                h.flush()
                h.close()
            except Exception:
                pass


def _attach_mcp_servers_mirror_handlers(
    log_dir: Path, fmt: logging.Formatter, *, primary_log_path: Path
) -> None:
    """将关键 logger 镜像到 mcp-servers.log（BizAPIClient + 指标钻取 HTTP，便于与 MCP 子进程同源排查）。"""
    mcp_path = (log_dir / "mcp-servers.log").resolve()
    if primary_log_path.resolve() == mcp_path:
        # MCP 子进程等：root 已写入 mcp-servers.log，再挂镜像会与 propagate 重复打两条
        return
    for name in _MCP_SERVERS_MIRROR_LOGGERS:
        lg = logging.getLogger(name)
        if any(getattr(h, _MCP_SERVERS_MIRROR_ATTR, False) for h in lg.handlers):
            continue
        fh = logging.handlers.RotatingFileHandler(
            str(mcp_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        fh.addFilter(TraceIdFilter())
        fh.addFilter(ExtraContextFilter())
        setattr(fh, _MCP_SERVERS_MIRROR_ATTR, True)
        lg.addHandler(fh)
        if name == "src.mcp_servers.biz_api_client":
            lg.setLevel(logging.DEBUG)


def _undefer_loggers_after_fileconfig() -> None:
    """fileConfig(disable_existing_loggers=True) 会把已存在的 Logger 标为 disabled；仅清 src.* / uvicorn.*。"""
    for name, ref in list(logging.Logger.manager.loggerDict.items()):
        if not isinstance(ref, logging.Logger) or not ref.disabled:
            continue
        if name == "src" or name.startswith("src.") or name.startswith("uvicorn"):
            ref.disabled = False


def setup_logging(
    file_stem: str, console: bool = True, json_logs: Optional[bool] = None
) -> None:
    """初始化日志。MCP 子进程须传 console=False，避免 stderr 干扰 stdio 协议。

    json_logs 为 None 时：全部 stem 使用易读文本；需要结构化行可传 ``json_logs=True``。
    """
    s = get_settings()
    level = getattr(logging, s.log_level.upper(), logging.INFO)
    log_dir = Path(s.log_dir)
    if not log_dir.is_absolute():
        log_dir = (_REPO_ROOT / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{file_stem}.log"

    # 同一进程内若先 ops-brain 再 mcp-servers，旧的 biz_api 镜像 handler 会残留，
    # 与 root 同写 mcp-servers.log 导致重复行。
    for _name in _MCP_SERVERS_MIRROR_LOGGERS:
        _remove_mcp_servers_mirror_handlers(logging.getLogger(_name))

    root = logging.getLogger()
    for h in root.handlers[:]:
        try:
            h.flush()
            h.close()
        except Exception:
            pass
        root.removeHandler(h)
    root.setLevel(level)

    if json_logs is None:
        json_logs = False
    fmt: logging.Formatter = _json_formatter() if json_logs else _plain_formatter()
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

    _attach_mcp_servers_mirror_handlers(log_dir, fmt, primary_log_path=log_path)
    _undefer_loggers_after_fileconfig()
    root.info("日志已初始化 | log_path=%s", str(log_path))
