from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

# 与 CWD 无关：始终尝试加载仓库根目录 .env（避免从子目录启动时仍用默认 effect_track_delay_days=7）
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"

# 诊断等业务时间统一按中国时区落库（ISO 8601 带 +08:00），前端可直接展示无需换算
CN_TZ = ZoneInfo("Asia/Shanghai")


class Settings(BaseSettings):
    postgres_uri: str = "postgresql://postgres:password@localhost:5432/ops_brain"
    wlwq_postgres_uri: str | None = None  # wlwq 模拟业务库，不设则 wlwq 用 POSTGRES_URI
    # Docker 内需指向服务名，如 http://wlwq-enterprise:8200（覆盖 tenant_registry 中 wlwq_local 的 api_base_url）
    wlwq_business_api_base: str | None = None
    # 平台中台（全局唯一，不写入 tenant_registry）。MCP 连接池仍用 tenant_id=__platform__ 作键，仅表示「中台」这一逻辑目标。
    platform_center_api_base: str | None = None
    platform_center_auth_type: str = "token"  # token | hmac，与中台网关约定一致
    platform_center_auth_credential: str = ""  # 明文或经 CREDENTIAL_ENCRYPT_KEY 加密；无企业上下文的中台请求兜底
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_model: str = "qwen3.5-plus"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_enabled: bool = True

    credential_encrypt_key: str = ""

    diagnosis_lookback_days: int = 90
    # 租户解析 Redis 缓存 TTL（秒）。<=0 时不读写 Redis，每次从 PG 加载（鉴权与 base_url 即时生效，QPS 高时慎用）
    tenant_cache_ttl: int = 600
    benchmark_cache_ttl: int = 600

    # 为 True 时启用旧版双轨：先按 5.2.3 单独落库 rule_5.2.3 任务并执行规则券/消息；为 False（默认）时仅采纳方案落库
    exec_push_rule_tasks: bool = True

    # 方案执行后延迟多少天再执行效果追踪复盘（0 = 立即执行，不延迟）
    effect_track_delay_days: int = 7

    # 追踪期间每隔多少天采集一次指标快照（0 = 不采集快照）
    effect_snapshot_interval_days: int = 3

    log_dir: str = "logs"
    log_level: str = "DEBUG"  # DEBUG / INFO / WARNING / ERROR

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
