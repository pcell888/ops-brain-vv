from functools import lru_cache
import logging
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 与 CWD 无关：始终尝试加载仓库根目录 .env
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"

# 诊断等业务时间统一按中国时区落库（ISO 8601 带 +08:00），前端可直接展示无需换算
CN_TZ = ZoneInfo("Asia/Shanghai")


class Settings(BaseSettings):
    postgres_uri: str = "postgresql://postgres:password@localhost:5432/ops_brain"
    # 平台中台（全局唯一，不写入 tenant_registries）。MCP 连接池仍用 tenant_id=__platform__ 作键，仅表示「中台」这一逻辑目标。
    platform_center_api_base: str | None = None
    platform_center_auth_type: str = "token"  # token | hmac，与中台网关约定一致
    platform_center_auth_credential: str = ""  # 明文；无企业上下文的中台请求兜底
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_provider: str = "dashscope"
    llm_model: str = "qwen3.5-plus"
    # 根因 / 方案 / 复盘（含追踪复盘报告 LLM）各自模型，互不回退至 llm_model
    llm_model_root_cause: str = "qwen3.5-flash"
    llm_model_solution: str = "qwen3.5-flash"
    llm_model_review: str = "qwen3.5-plus"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_enabled: bool = True
    # 是否启用模型深度思考（reasoning）模式；qwen3.5 系列关闭后可省 60-70% 推理 token，大幅提速
    llm_thinking_enabled: bool = False
    # 兼容模式接口首包可能较慢；可用环境变量 LLM_HTTP_READ_TIMEOUT 覆盖（秒）
    llm_http_read_timeout: float = 300.0

    diagnosis_lookback_days: int = 90
    # 租户解析 Redis 缓存 TTL（秒）。<=0 时不读写 Redis，每次从 PG 加载（鉴权与 base_url 即时生效，QPS 高时慎用）
    tenant_cache_ttl: int = 600
    benchmark_cache_ttl: int = 600

    # 为 True 时启用旧版双轨：先按 5.2.3 单独落库 rule_5.2.3 任务并执行规则券/消息；为 False（默认）时仅采纳方案落库
    exec_push_rule_tasks: bool = False

    # 方案执行后延迟多少「天」再进入效果追踪复盘（0 = 立即；可用小数，如 2/24≈0.083 表示约 2 小时）
    effect_track_delay_days: float = 7.0

    # 自动快照：同一追踪两次快照至少间隔多少「天」（支持小数，如 1/24≈0.042 表示约 1 小时）；0=不限制间隔（每次整点候选）
    effect_snapshot_interval_days: float = Field(default=1.0, ge=0.0, le=366.0)
    # 每日整点尝试跑一轮快照采集（与 interval_days 配合节流；中国时区）
    effect_snapshot_hour: int = Field(default=3, ge=0, le=23)

    # 每日整点扫描「复盘已到期」并恢复 track_effects（中国时区）
    effect_review_checker_hour: int = Field(default=4, ge=0, le=23)

    log_dir: str = "logs"
    log_level: str = "DEBUG"  # DEBUG / INFO / WARNING / ERROR

    def llm_httpx_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=30.0,
            read=self.llm_http_read_timeout,
            write=30.0,
            pool=30.0,
        )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def format_delay_days_zh(days: float) -> str:
    """将延迟天数格式化为简短中文（用于进度文案）；支持小数天。"""
    d = max(0.0, float(days))
    if d <= 0:
        return "立即"
    if d >= 1 and abs(d - round(d)) < 1e-9:
        n = int(round(d))
        return f"{n} 天" if n != 1 else "1 天"
    mins = int(round(d * 24 * 60))
    if mins <= 0:
        return "立即"
    if mins < 60:
        return f"{mins} 分钟"
    hrs = d * 24
    if abs(hrs - round(hrs)) < 1e-9:
        nh = int(round(hrs))
        return f"{nh} 小时"
    return f"{hrs:.1f} 小时"


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
        "%s | LLM provider=%s model=%s root_cause=%s solution=%s review=%s base_url=%s enabled=%s thinking=%s timeout_read=%s api_key_set=%s",
        prefix,
        st.llm_provider,
        st.llm_model,
        st.llm_model_root_cause,
        st.llm_model_solution,
        st.llm_model_review,
        st.llm_base_url,
        st.llm_enabled,
        st.llm_thinking_enabled,
        st.llm_http_read_timeout,
        has_llm_key,
    )
    log.info(
        "%s | DB postgres=%s redis=%s",
        prefix,
        _uri_host_db(st.postgres_uri),
        _redis_host_db(st.redis_url),
    )
    snap_iv = float(st.effect_snapshot_interval_days)
    log.info(
        "%s | effect_track_delay_days=%s snapshot: 间隔≥%s天 @%02d:00 | effect_review_checker: 每日%02d:00",
        prefix,
        st.effect_track_delay_days,
        snap_iv,
        st.effect_snapshot_hour,
        st.effect_review_checker_hour,
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
