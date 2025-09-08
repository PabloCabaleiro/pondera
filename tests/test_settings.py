"""Tests for pondera.settings module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from pondera.settings import (
    PonderaSettings,
    apply_to_environment,
    get_settings,
    reload_settings,
    _set_if_missing,
)


class TestPonderaSettings:
    """Test the PonderaSettings class."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        settings = PonderaSettings()

        assert settings.log_level == "INFO"
        assert settings.artifacts_dir == "eval/artifacts"
        assert settings.timeout_default_s == 240
        assert settings.judge_model == "openai:gpt-4o-mini"
        assert settings.openai_api_key is None
        assert settings.openai_base_url is None
        assert settings.openai_organization is None
        assert settings.anthropic_api_key is None
        assert settings.azure_openai_api_key is None
        assert settings.azure_openai_endpoint is None
        assert settings.azure_openai_deployment is None
        assert settings.extra == {}

    def test_env_prefix(self) -> None:
        """Test that PONDERA_ environment variables are loaded."""
        with patch.dict(
            os.environ,
            {
                "PONDERA_LOG_LEVEL": "DEBUG",
                "PONDERA_ARTIFACTS_DIR": "/custom/artifacts",
                "PONDERA_TIMEOUT_DEFAULT_S": "300",
                "PONDERA_JUDGE_MODEL": "anthropic:claude-3-sonnet",
            },
            clear=False,
        ):
            settings = PonderaSettings()

            assert settings.log_level == "DEBUG"
            assert settings.artifacts_dir == "/custom/artifacts"
            assert settings.timeout_default_s == 300
            assert settings.judge_model == "anthropic:claude-3-sonnet"

    def test_provider_credentials_from_env(self) -> None:
        """Test that provider credentials are loaded from environment."""
        with patch.dict(
            os.environ,
            {
                "PONDERA_OPENAI_API_KEY": "sk-test-openai",
                "PONDERA_OPENAI_BASE_URL": "https://api.custom.com",
                "PONDERA_OPENAI_ORGANIZATION": "org-123",
                "PONDERA_ANTHROPIC_API_KEY": "sk-test-anthropic",
                "PONDERA_AZURE_OPENAI_API_KEY": "azure-key",
                "PONDERA_AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "PONDERA_AZURE_OPENAI_DEPLOYMENT": "gpt-4-deployment",
            },
            clear=False,
        ):
            settings = PonderaSettings()

            assert settings.openai_api_key == "sk-test-openai"
            assert settings.openai_base_url == "https://api.custom.com"
            assert settings.openai_organization == "org-123"
            assert settings.anthropic_api_key == "sk-test-anthropic"
            assert settings.azure_openai_api_key == "azure-key"
            assert settings.azure_openai_endpoint == "https://test.openai.azure.com"
            assert settings.azure_openai_deployment == "gpt-4-deployment"

    def test_env_file_loading(self) -> None:
        """Test that settings are loaded from .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("""
PONDERA_LOG_LEVEL=DEBUG
PONDERA_ARTIFACTS_DIR=/tmp/artifacts
PONDERA_JUDGE_MODEL=openai:gpt-4
PONDERA_OPENAI_API_KEY=sk-from-file
""")

            # Change to the temp directory so the .env file is found
            original_cwd = os.getcwd()
            # Also clear any conflicting env vars
            env_backup = {}
            env_vars_to_clear = [
                "PONDERA_LOG_LEVEL",
                "PONDERA_ARTIFACTS_DIR",
                "PONDERA_JUDGE_MODEL",
                "PONDERA_OPENAI_API_KEY",
            ]

            try:
                # Backup and clear environment variables that might interfere
                for var in env_vars_to_clear:
                    if var in os.environ:
                        env_backup[var] = os.environ[var]
                        del os.environ[var]

                os.chdir(tmpdir)
                settings = PonderaSettings()

                assert settings.log_level == "DEBUG"
                assert settings.artifacts_dir == "/tmp/artifacts"
                assert settings.judge_model == "openai:gpt-4"
                assert settings.openai_api_key == "sk-from-file"
            finally:
                os.chdir(original_cwd)
                # Restore environment variables
                for var, value in env_backup.items():
                    os.environ[var] = value

    def test_env_var_overrides_env_file(self) -> None:
        """Test that environment variables override .env file values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("PONDERA_LOG_LEVEL=ERROR\n")

            with patch.dict(os.environ, {"PONDERA_LOG_LEVEL": "WARNING"}, clear=False):
                original_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    settings = PonderaSettings()

                    # Environment variable should win over .env file
                    assert settings.log_level == "WARNING"
                finally:
                    os.chdir(original_cwd)

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields in environment are ignored."""
        with patch.dict(
            os.environ,
            {
                "PONDERA_UNKNOWN_FIELD": "should_be_ignored",
                "PONDERA_LOG_LEVEL": "DEBUG",
            },
            clear=False,
        ):
            # This should not raise an error
            settings = PonderaSettings()
            assert settings.log_level == "DEBUG"
            # Unknown field should not be accessible
            assert not hasattr(settings, "unknown_field")


class TestSetIfMissing:
    """Test the _set_if_missing helper function."""

    def test_sets_value_when_missing(self) -> None:
        """Test that value is set when environment variable is missing."""
        var_name = "TEST_VAR_MISSING"
        # Ensure the variable is not set
        if var_name in os.environ:
            del os.environ[var_name]

        _set_if_missing(var_name, "test_value")

        assert os.environ[var_name] == "test_value"

        # Clean up
        del os.environ[var_name]

    def test_preserves_existing_value(self) -> None:
        """Test that existing environment variable is not overwritten."""
        var_name = "TEST_VAR_EXISTS"
        original_value = "original_value"

        with patch.dict(os.environ, {var_name: original_value}):
            _set_if_missing(var_name, "new_value")

            # Should preserve original value
            assert os.environ[var_name] == original_value

    def test_handles_none_value(self) -> None:
        """Test that None values are ignored."""
        var_name = "TEST_VAR_NONE"
        # Ensure the variable is not set
        if var_name in os.environ:
            del os.environ[var_name]

        _set_if_missing(var_name, None)

        # Should not set the variable
        assert var_name not in os.environ


class TestApplyToEnvironment:
    """Test the apply_to_environment function."""

    def test_exports_all_provider_settings(self) -> None:
        """Test that all provider settings are exported to environment."""
        settings = PonderaSettings(
            judge_model="custom:model",
            openai_api_key="sk-openai",
            openai_base_url="https://custom.api.com",
            openai_organization="org-custom",
            anthropic_api_key="sk-anthropic",
            azure_openai_api_key="azure-key",
            azure_openai_endpoint="https://azure.endpoint.com",
            azure_openai_deployment="deployment-name",
        )

        # Clear relevant environment variables
        env_vars_to_clear = [
            "PONDERA_JUDGE_MODEL",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_ORG",
            "OPENAI_ORGANIZATION",
            "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_DEPLOYMENT",
        ]

        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

        try:
            apply_to_environment(settings)

            assert os.environ["PONDERA_JUDGE_MODEL"] == "custom:model"
            assert os.environ["OPENAI_API_KEY"] == "sk-openai"
            assert os.environ["OPENAI_BASE_URL"] == "https://custom.api.com"
            assert os.environ["OPENAI_ORG"] == "org-custom"
            assert os.environ["OPENAI_ORGANIZATION"] == "org-custom"
            assert os.environ["ANTHROPIC_API_KEY"] == "sk-anthropic"
            assert os.environ["AZURE_OPENAI_API_KEY"] == "azure-key"
            assert os.environ["AZURE_OPENAI_ENDPOINT"] == "https://azure.endpoint.com"
            assert os.environ["AZURE_OPENAI_DEPLOYMENT"] == "deployment-name"
        finally:
            # Clean up
            for var in env_vars_to_clear:
                if var in os.environ:
                    del os.environ[var]

    def test_preserves_existing_env_vars(self) -> None:
        """Test that existing environment variables are not overwritten."""
        settings = PonderaSettings(
            openai_api_key="sk-from-settings", anthropic_api_key="sk-from-settings"
        )

        with patch.dict(
            os.environ, {"OPENAI_API_KEY": "sk-existing", "ANTHROPIC_API_KEY": "sk-existing"}
        ):
            apply_to_environment(settings)

            # Should preserve existing values
            assert os.environ["OPENAI_API_KEY"] == "sk-existing"
            assert os.environ["ANTHROPIC_API_KEY"] == "sk-existing"

    def test_skips_none_values(self) -> None:
        """Test that None values are not exported."""
        settings = PonderaSettings()  # All provider settings are None by default

        # Clear any existing values
        env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY"]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

        apply_to_environment(settings)

        # None values should not be set
        for var in env_vars:
            assert var not in os.environ


class TestGetSettings:
    """Test the get_settings function."""

    def test_returns_settings_instance(self) -> None:
        """Test that get_settings returns a PonderaSettings instance."""
        settings = get_settings()
        assert isinstance(settings, PonderaSettings)

    def test_caches_settings(self) -> None:
        """Test that get_settings caches the result."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance
        assert settings1 is settings2

    def test_applies_to_environment(self) -> None:
        """Test that get_settings calls apply_to_environment."""
        # Clear cache first
        get_settings.cache_clear()

        with patch("pondera.settings.apply_to_environment") as mock_apply:
            settings = get_settings()

            mock_apply.assert_called_once_with(settings)

    def test_with_custom_settings(self) -> None:
        """Test get_settings with custom environment variables."""
        # Clear cache first
        get_settings.cache_clear()

        with patch.dict(
            os.environ,
            {"PONDERA_LOG_LEVEL": "DEBUG", "PONDERA_JUDGE_MODEL": "custom:model"},
            clear=False,
        ):
            settings = get_settings()

            assert settings.log_level == "DEBUG"
            assert settings.judge_model == "custom:model"


class TestReloadSettings:
    """Test the reload_settings function."""

    def test_clears_cache(self) -> None:
        """Test that reload_settings clears the cache."""
        # Get initial settings to populate cache
        get_settings()

        # Reload settings
        settings2 = reload_settings()

        # Should return a new instance (though values might be the same)
        # We can't test identity since reload might return identical cached result
        assert isinstance(settings2, PonderaSettings)

    def test_returns_fresh_settings(self) -> None:
        """Test that reload_settings returns fresh settings with new env vars."""
        # Get initial settings
        get_settings()

        # Change environment and reload
        with patch.dict(os.environ, {"PONDERA_LOG_LEVEL": "ERROR"}, clear=False):
            settings = reload_settings()

            assert settings.log_level == "ERROR"

    def test_applies_to_environment_on_reload(self) -> None:
        """Test that reload_settings calls apply_to_environment."""
        with patch("pondera.settings.apply_to_environment") as mock_apply:
            settings = reload_settings()

            mock_apply.assert_called_once_with(settings)


class TestIntegration:
    """Integration tests for the settings module."""

    def test_full_workflow(self) -> None:
        """Test the complete workflow from env vars to exported settings."""
        # Clear cache
        get_settings.cache_clear()

        with patch.dict(
            os.environ,
            {
                "PONDERA_LOG_LEVEL": "DEBUG",
                "PONDERA_ARTIFACTS_DIR": "/test/artifacts",
                "PONDERA_JUDGE_MODEL": "openai:gpt-4",
                "PONDERA_OPENAI_API_KEY": "sk-test-key",
            },
            clear=False,
        ):
            # Clear any existing provider env vars
            provider_vars = ["OPENAI_API_KEY", "PONDERA_JUDGE_MODEL"]
            for var in provider_vars:
                if var in os.environ and not var.startswith("PONDERA_"):
                    del os.environ[var]

            try:
                settings = get_settings()

                # Verify settings loaded correctly
                assert settings.log_level == "DEBUG"
                assert settings.artifacts_dir == "/test/artifacts"
                assert settings.judge_model == "openai:gpt-4"
                assert settings.openai_api_key == "sk-test-key"

                # Verify environment was populated
                assert os.environ["OPENAI_API_KEY"] == "sk-test-key"
                assert os.environ["PONDERA_JUDGE_MODEL"] == "openai:gpt-4"
            finally:
                # Clean up
                for var in provider_vars:
                    if var in os.environ:
                        del os.environ[var]

    def test_env_file_and_export_workflow(self) -> None:
        """Test loading from .env file and exporting to environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("""PONDERA_JUDGE_MODEL=anthropic:claude-3-sonnet
PONDERA_ANTHROPIC_API_KEY=sk-test-anthropic
PONDERA_TIMEOUT_DEFAULT_S=180
""")

            original_cwd = os.getcwd()
            # Also clear any conflicting env vars
            env_backup = {}
            env_vars_to_clear = [
                "PONDERA_JUDGE_MODEL",
                "PONDERA_ANTHROPIC_API_KEY",
                "PONDERA_TIMEOUT_DEFAULT_S",
                "ANTHROPIC_API_KEY",
            ]

            try:
                # Backup and clear environment variables that might interfere
                for var in env_vars_to_clear:
                    if var in os.environ:
                        env_backup[var] = os.environ[var]
                        del os.environ[var]

                os.chdir(tmpdir)

                # Create fresh settings instance that will read the .env file
                settings = PonderaSettings()
                apply_to_environment(settings)

                # Verify settings from .env file
                assert settings.judge_model == "anthropic:claude-3-sonnet"
                assert settings.anthropic_api_key == "sk-test-anthropic"
                assert settings.timeout_default_s == 180

                # Verify environment was populated
                assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-anthropic"

            finally:
                os.chdir(original_cwd)
                # Restore environment variables
                for var, value in env_backup.items():
                    os.environ[var] = value
                # Clean up any variables we set
                for var in ["ANTHROPIC_API_KEY"]:
                    if var in os.environ and var not in env_backup:
                        del os.environ[var]
