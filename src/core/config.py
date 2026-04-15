from functools import lru_cache
import logging
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

# 与 CWD 无关：始终尝试加载仓库根目录 .env（避免从子目录启动时仍用默认 effect_track_delay_days=7）
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"

# 诊断等业务时间统一按中国时区落库（ISO 8601 带 +08:00），前端可直接展示无需换算
CN_TZ = ZoneInfo("Asia/Shanghai")


class Settings(BaseSettings):
    postgres_uri: str = "postgresql://postgres:password@localhost:5432/ops_brain"
    # 平台中台（全局唯一，不写入 tenant_registry）。MCP 连接池仍用 tenant_id=__platform__ 作键，仅表示「中台」这一逻辑目标。
    platform_center_api_base: str | None = None
    platform_center_auth_type: str = "token"  # token | hmac，与中台网关约定一致
    platform_center_auth_credential: str = ""  # 明文；无企业上下文的中台请求兜底
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_provider: str = "dashscope"
    llm_model: str = "qwen3.5-plus"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_enabled: bool = True
    # 兼容模式接口首包可能较慢；可用环境变量 LLM_HTTP_READ_TIMEOUT 覆盖（秒）
    llm_http_read_timeout: float = 300.0

    diagnosis_lookback_days: int = 90
    # 租户解析 Redis 缓存 TTL（秒）。<=0 时不读写 Redis，每次从 PG 加载（鉴权与 base_url 即时生效，QPS 高时慎用）
    tenant_cache_ttl: int = 600
    benchmark_cache_ttl: int = 600

    # 为 True 时启用旧版双轨：先按 5.2.3 单独落库 rule_5.2.3 任务并执行规则券/消息；为 False（默认）时仅采纳方案落库
    exec_push_rule_tasks: bool = False

    # 方案执行后延迟多少天再执行效果追踪复盘（0 = 立即执行，不延迟）
    effect_track_delay_days: int = 7

    # 追踪期间每隔多少天采集一次指标快照（0 = 不采集快照）
    effect_snapshot_interval_days: int = 3

    log_dir: str = "logs"
    log_level: str = "DEBUG"  # DEBUG / INFO / WARNING / ERROR

    def llm_httpx_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=10.0,
            read=self.llm_http_read_timeout,
            write=10.0,
            pool=10.0,
        )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _uri_host_db(uri: str) -> str:
    """日志用：主机 + 库名，不含口令。"""
    try:
        u = urlparse(uri.replace("postgresql+asyncpg://", "postgresql://", 1))
        host = u.hostname or "?"
        port = f":{u.port}" if u.port else ""
        db = (u.path or "/").strip("/").split("/")[0] or "?"
        return f"{host}{port}/{db}"
    except Exception:
        return "?"


def _redis_host_db(uri: str) -> str:
    try:
        u = urlparse(uri.replace("rediss://", "https://", 1).replace("redis://", "http://", 1))
        host = u.hostname or "?"
        port = f":{u.port}" if u.port else ""
        tail = (u.path or "/").strip("/") or "0"
        return f"{host}{port}/{tail}"
    except Exception:
        return "?"


def log_diagnosis_service_config(logger: logging.Logger | None = None, *, prefix: str = "诊断服务") -> None:
    """打印当前诊断相关配置（脱敏）。供 make dev / uvicorn 启动或排障时核对 .env 是否生效。"""
    log = logger or logging.getLogger("ops-brain.config")
    st = get_settings()
    has_llm_key = bool((st.llm_api_key or "").strip())
    log.info(
        "%s | env_file=%s exists=%s",
        prefix,
        _ENV_FILE,
        _ENV_FILE.is_file(),
    )
    log.info(
        "%s | LLM provider=%s model=%s base_url=%s enabled=%s timeout_read=%s api_key_set=%s",
        prefix,
        st.llm_provider,
        st.llm_model,
        st.llm_base_url,
        st.llm_enabled,
        st.llm_http_read_timeout,
        has_llm_key,
    )
    log.info(
        "%s | DB postgres=%s redis=%s",
        prefix,
        _uri_host_db(st.postgres_uri),
        _redis_host_db(st.redis_url),
    )


def log_diagnosis_run_context(
    logger: logging.Logger | None,
    *,
    thread_id: str,
    tenant_id: str,
    store_id: str,
    trigger_type: str,
) -> None:
    """单次诊断任务开始时一行摘要。"""
    log = logger or logging.getLogger("ops-brain.diagnosis")
    st = get_settings()
    log.info(
        "诊断运行 | thread_id=%s tenant=%s store=%s trigger=%s | llm_enabled=%s",
        thread_id,
        tenant_id,
        store_id,
        trigger_type,
        st.llm_enabled,
    )
