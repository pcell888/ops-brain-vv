"""随机工具 — 环境变量控制随机区间。"""

from __future__ import annotations

import os
import random


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def random_enabled(use_random: bool | None) -> bool:
    if use_random is not None:
        return use_random
    return env_bool("WLWQ_USE_RANDOM", default=True)


def use_random_from_params(params: dict) -> bool | None:
    v = params.get("useRandom")
    if isinstance(v, str):
        return v.lower() in ("1", "true", "yes")
    if isinstance(v, bool):
        return v
    return None


def query_param_bool(params: dict, key: str, default: bool = False) -> bool:
    v = params.get(key, default)
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def random_int(min_key: str, max_key: str, default_min: int, default_max: int) -> int:
    min_v = int(os.getenv(min_key, str(default_min)))
    max_v = int(os.getenv(max_key, str(default_max)))
    if min_v > max_v:
        min_v, max_v = max_v, min_v
    return random.randint(min_v, max_v)


def random_float(min_key: str, max_key: str, default_min: float, default_max: float, ndigits: int = 2) -> float:
    min_v = float(os.getenv(min_key, str(default_min)))
    max_v = float(os.getenv(max_key, str(default_max)))
    if min_v > max_v:
        min_v, max_v = max_v, min_v
    return round(random.uniform(min_v, max_v), ndigits)
