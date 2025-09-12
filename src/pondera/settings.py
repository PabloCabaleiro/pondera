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
      - All Pondera-specific vars use the PONDERA_ prefix.
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

    # Provider creds / endpoints (optional; export to generic envs for SDKs)
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_organization: str | None = None

    anthropic_api_key: str | None = None

    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None

    # Model configuration
    model_timeout: int = 120
    model_family: str | None = None

    # Azure models (additional fields)
    azure_model_name: str | None = None
    azure_openai_api_version: str | None = None

    # OpenAI models (additional fields)
    openai_model_name: str | None = None

    # Ollama models
    ollama_url: str | None = None
    ollama_model_name: str | None = None

    # OpenRouter models
    openrouter_api_key: str | None = None
    openrouter_api_url: str = "https://openrouter.ai/api/v1"
    openrouter_model_name: str | None = None

    # Embeddings
    vdb_embeddings_model_family: str | None = None
    openai_vdb_embeddings_model_name: str | None = None
    azure_vdb_embeddings_model_name: str | None = None
    ollama_vdb_embeddings_model_name: str | None = None

    # Bedrock models
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    bedrock_model_name: str | None = None

    # Space for future providers; keep names intuitive and documented.
    extra: dict[str, Any] = Field(default_factory=dict)


def _set_if_missing(name: str, value: str | None) -> None:
    if value is None:
        return
    os.environ.setdefault(name, value)


def _set_if_missing_int(name: str, value: int) -> None:
    os.environ.setdefault(name, str(value))


def apply_to_environment(settings: PonderaSettings) -> None:
    """
    Export provider-specific variables so downstream libraries (OpenAI, Anthropic, Azure)
    and pydantic_ai can auto-discover credentials without every component importing envs.

    We set only if the env var is not already present (user wins).
    """

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

    # Additional model configuration
    _set_if_missing_int("MODEL_TIMEOUT", settings.model_timeout)
    _set_if_missing("MODEL_FAMILY", settings.model_family)

    # Azure models (additional)
    _set_if_missing("AZURE_MODEL_NAME", settings.azure_model_name)
    _set_if_missing("AZURE_OPENAI_API_VERSION", settings.azure_openai_api_version)

    # OpenAI models (additional)
    _set_if_missing("OPENAI_MODEL_NAME", settings.openai_model_name)

    # Ollama models
    _set_if_missing("OLLAMA_URL", settings.ollama_url)
    _set_if_missing("OLLAMA_MODEL_NAME", settings.ollama_model_name)

    # OpenRouter models
    _set_if_missing("OPENROUTER_API_KEY", settings.openrouter_api_key)
    _set_if_missing("OPENROUTER_API_URL", settings.openrouter_api_url)
    _set_if_missing("OPENROUTER_MODEL_NAME", settings.openrouter_model_name)

    # Embeddings
    _set_if_missing("VDB_EMBEDDINGS_MODEL_FAMILY", settings.vdb_embeddings_model_family)
    _set_if_missing("OPENAI_VDB_EMBEDDINGS_MODEL_NAME", settings.openai_vdb_embeddings_model_name)
    _set_if_missing("AZURE_VDB_EMBEDDINGS_MODEL_NAME", settings.azure_vdb_embeddings_model_name)
    _set_if_missing("OLLAMA_VDB_EMBEDDINGS_MODEL_NAME", settings.ollama_vdb_embeddings_model_name)

    # Bedrock models
    _set_if_missing("AWS_ACCESS_KEY_ID", settings.aws_access_key_id)
    _set_if_missing("AWS_SECRET_ACCESS_KEY", settings.aws_secret_access_key)
    _set_if_missing("AWS_SESSION_TOKEN", settings.aws_session_token)
    _set_if_missing("AWS_REGION", settings.aws_region)
    _set_if_missing("AWS_PROFILE", settings.aws_profile)
    _set_if_missing("BEDROCK_MODEL_NAME", settings.bedrock_model_name)


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
    get_settings.cache_clear()
    return get_settings()
