"""Core settings for the Cadence library.

Focused configuration for the shared judgment layer and the macro context engine:
the Jev access route, the on-disk HTTP cache, and the GDELT throttle. No trading
gates live here — this package moves no money.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

# python-dotenv is optional: tests run without it and without a .env file.
if importlib.util.find_spec("dotenv") is not None:
    from dotenv import load_dotenv

    load_dotenv()

DEFAULT_USER_AGENT = "cadence-core/0.1 (+https://github.com/cadence-trading)"


class ConfigError(RuntimeError):
    """Raised when the environment contains an invalid configuration."""


@dataclass(frozen=True)
class Settings:
    jev_api_key: str | None
    jev_base_url: str
    jev_model: str
    cache_dir: Path
    http_timeout: float
    gdelt_min_interval: float
    user_agent: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        return cls(
            jev_api_key=env.get("JEV_API_KEY") or None,
            jev_base_url=env.get("JEV_BASE_URL") or "https://api.typesafe.ai",
            jev_model=env.get("JEV_MODEL") or "jev",
            cache_dir=Path(env.get("CADENCE_CACHE_DIR") or "var/http-cache"),
            http_timeout=_as_float(env.get("CADENCE_HTTP_TIMEOUT"), 15.0, "CADENCE_HTTP_TIMEOUT"),
            gdelt_min_interval=_as_float(env.get("GDELT_MIN_INTERVAL"), 5.0, "GDELT_MIN_INTERVAL"),
            user_agent=env.get("CADENCE_USER_AGENT") or DEFAULT_USER_AGENT,
        )


def _as_float(value: str | None, default: float, name: str) -> float:
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {value!r}") from exc


def load_settings(env: dict[str, str] | None = None) -> Settings:
    return Settings.from_env(env)
