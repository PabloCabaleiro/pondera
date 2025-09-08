# src/pondera/settings.py
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PonderaSettings(BaseSettings):
    """
    Centralized configuration for Pondera.

    Convention:
      - All Pondera-specific vars use the PONDERA_ prefix (e.g., PONDERA_JUDGE_MODEL).
      - We mirror common provider envs (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) by
        exporting them via `apply_to_environment()` so provider SDKs and pydantic_ai
        discover them without each runner/judge touching env directly.
    """

    model_config = SettingsConfigDict(
        env_prefix="PONDERA_",
        env_file=".env",
        extra="ignore",
    )

    # General
    log_level: str = "INFO"
    artifacts_dir: str = "eval/artifacts"
    timeout_default_s: int = 240

    # Judge defaults
    judge_model: str = Field(
        default="openai:gpt-4o-mini", description="Default model id for the judge"
    )

    # Provider creds / endpoints (optional; export to generic envs for SDKs)
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_organization: str | None = None

    anthropic_api_key: str | None = None

    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None

    # Space for future providers; keep names intuitive and documented.
    extra: dict[str, Any] = Field(default_factory=dict)


def _set_if_missing(name: str, value: str | None) -> None:
    if value is None:
        return
    os.environ.setdefault(name, value)


def apply_to_environment(settings: PonderaSettings) -> None:
    """
    Export provider-specific variables so downstream libraries (OpenAI, Anthropic, Azure)
    and pydantic_ai can auto-discover credentials without every component importing envs.

    We set only if the env var is not already present (user wins).
    """
    # Judge default model (for components that check it)
    _set_if_missing("PONDERA_JUDGE_MODEL", settings.judge_model)

    # OpenAI
    _set_if_missing("OPENAI_API_KEY", settings.openai_api_key)
    _set_if_missing("OPENAI_BASE_URL", settings.openai_base_url)
    # Different clients use different names; set both to be safe.
    _set_if_missing("OPENAI_ORG", settings.openai_organization)
    _set_if_missing("OPENAI_ORGANIZATION", settings.openai_organization)

    # Anthropic
    _set_if_missing("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    # Azure OpenAI
    _set_if_missing("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key)
    _set_if_missing("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint)
    _set_if_missing("AZURE_OPENAI_DEPLOYMENT", settings.azure_openai_deployment)


@lru_cache(maxsize=1)
def get_settings() -> PonderaSettings:
    """
    Load settings once (env/.env), export provider envs, and cache.
    """
    s = PonderaSettings()
    apply_to_environment(s)
    return s


def reload_settings() -> PonderaSettings:
    """
    Clear cache and reload; useful in tests.
    """
    get_settings.cache_clear()  # type: ignore[attr-defined]
    return get_settings()
