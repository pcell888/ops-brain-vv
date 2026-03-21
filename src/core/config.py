from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings

# 诊断等业务时间统一按中国时区落库（ISO 8601 带 +08:00），前端可直接展示无需换算
CN_TZ = ZoneInfo("Asia/Shanghai")


class Settings(BaseSettings):
    postgres_uri: str = "postgresql://postgres:password@localhost:5432/ops_brain"
    wlwq_postgres_uri: str | None = None  # wlwq 模拟业务库，不设则 wlwq 用 POSTGRES_URI
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_model: str = "qwen3.5-plus"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_enabled: bool = True

    credential_encrypt_key: str = ""

    diagnosis_lookback_days: int = 90
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
