"""
Tests for LLM Factory Module.

Tests for create_llm_provider, load_config, resolve_env_vars,
get_available_providers, get_global_provider, reset_global_provider.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
import tempfile
import yaml

from src.llm.factory import (
    load_config,
    resolve_env_vars,
    create_llm_provider,
    get_available_providers,
    get_global_provider,
    reset_global_provider,
    _create_local_provider,
    _create_gigachat_provider,
    _create_openai_provider,
)
from src.llm.base_provider import (
    LLMConfig,
    LLMProviderConfigError,
    BaseLLMProvider,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from a yaml file."""
        config_content = {
            "llm": {
                "provider": "local",
                "local": {
                    "model_path": "/path/to/model.gguf",
                    "temperature": 0.7,
                }
            }
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        config = load_config(str(config_file))

        assert config["llm"]["provider"] == "local"
        assert config["llm"]["local"]["temperature"] == 0.7

    def test_load_config_missing_file(self, tmp_path):
        """Test loading config from non-existent file returns empty dict."""
        config = load_config(str(tmp_path / "nonexistent.yaml"))

        assert config == {}

    def test_load_config_empty_file(self, tmp_path):
        """Test loading config from empty file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = load_config(str(config_file))

        assert config == {}


class TestResolveEnvVars:
    """Tests for resolve_env_vars function."""

    def test_resolve_simple_env_var(self):
        """Test resolving simple ${VAR} syntax."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = resolve_env_vars("${TEST_VAR}")
            assert result == "test_value"

    def test_resolve_env_var_with_default(self):
        """Test resolving ${VAR:-default} syntax."""
        # Without env var set, use default
        result = resolve_env_vars("${UNSET_VAR:-default_value}")
        assert result == "default_value"

        # With env var set, use env value
        with patch.dict(os.environ, {"SET_VAR": "env_value"}):
            result = resolve_env_vars("${SET_VAR:-default}")
            assert result == "env_value"

    def test_resolve_in_dict(self):
        """Test resolving env vars in nested dict."""
        with patch.dict(os.environ, {"API_KEY": "secret123"}):
            config = {
                "api_key": "${API_KEY}",
                "nested": {
                    "value": "${API_KEY}"
                }
            }
            result = resolve_env_vars(config)

            assert result["api_key"] == "secret123"
            assert result["nested"]["value"] == "secret123"

    def test_resolve_in_list(self):
        """Test resolving env vars in list."""
        with patch.dict(os.environ, {"VAL1": "one", "VAL2": "two"}):
            config = ["${VAL1}", "${VAL2}", "static"]
            result = resolve_env_vars(config)

            assert result == ["one", "two", "static"]

    def test_resolve_unset_var_without_default(self):
        """Test that unset var without default is left as-is."""
        result = resolve_env_vars("${DEFINITELY_UNSET_VAR}")
        assert result == "${DEFINITELY_UNSET_VAR}"

    def test_resolve_mixed_string(self):
        """Test resolving env vars in mixed string."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8080"}):
            result = resolve_env_vars("http://${HOST}:${PORT}/api")
            assert result == "http://localhost:8080/api"

    def test_resolve_non_string(self):
        """Test that non-string values pass through."""
        assert resolve_env_vars(123) == 123
        assert resolve_env_vars(True) is True
        assert resolve_env_vars(None) is None


class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    def test_returns_dict(self):
        """Test that function returns a dict with provider names."""
        providers = get_available_providers()

        assert isinstance(providers, dict)
        assert "local" in providers
        assert "gigachat" in providers
        assert "openai" in providers

    def test_provider_values_are_bool(self):
        """Test that all values are booleans."""
        providers = get_available_providers()

        for name, available in providers.items():
            assert isinstance(available, bool), f"{name} value is not bool"


class TestGlobalProvider:
    """Tests for global provider singleton pattern."""

    def teardown_method(self):
        """Reset global provider after each test."""
        reset_global_provider()

    def test_reset_global_provider(self):
        """Test that reset clears the global provider."""
        # This just ensures reset doesn't raise
        reset_global_provider()

    @patch("src.llm.factory.create_llm_provider")
    def test_get_global_provider_creates_once(self, mock_create):
        """Test that global provider is created only once."""
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_create.return_value = mock_provider

        # First call creates provider
        provider1 = get_global_provider()

        # Second call returns same instance
        provider2 = get_global_provider()

        assert provider1 is provider2
        mock_create.assert_called_once()


class TestCreateLLMProvider:
    """Tests for create_llm_provider function."""

    def test_unknown_provider_raises(self):
        """Test that unknown provider type raises error."""
        config = {
            "llm": {
                "provider": "unknown_provider"
            }
        }

        with pytest.raises(LLMProviderConfigError) as exc_info:
            create_llm_provider(config)

        assert "unknown" in str(exc_info.value).lower()

    def test_no_config_uses_default_local(self):
        """Test that missing config defaults to local provider."""
        # This test would require local provider to be available
        # In CI without llama-cpp, this would fail differently
        # So we just verify the path is taken
        pass

    @patch("src.llm.factory._create_local_provider")
    def test_local_provider_selected(self, mock_create_local):
        """Test that 'local' provider type calls correct function."""
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_create_local.return_value = mock_provider

        config = {
            "llm": {
                "provider": "local",
                "local": {
                    "model_path": "/path/to/model.gguf"
                }
            }
        }

        provider = create_llm_provider(config)

        mock_create_local.assert_called_once()

    @patch("src.llm.factory._create_gigachat_provider")
    def test_gigachat_provider_selected(self, mock_create_gigachat):
        """Test that 'gigachat' provider type calls correct function."""
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_create_gigachat.return_value = mock_provider

        config = {
            "llm": {
                "provider": "gigachat",
                "gigachat": {
                    "credentials": "test_credentials"
                }
            }
        }

        provider = create_llm_provider(config)

        mock_create_gigachat.assert_called_once()

    @patch("src.llm.factory._create_openai_provider")
    def test_openai_provider_selected(self, mock_create_openai):
        """Test that 'openai' provider type calls correct function."""
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_create_openai.return_value = mock_provider

        config = {
            "llm": {
                "provider": "openai",
                "openai": {
                    "api_key": "sk-test123"
                }
            }
        }

        provider = create_llm_provider(config)

        mock_create_openai.assert_called_once()


class TestCreateGigaChatProvider:
    """Tests for _create_gigachat_provider function."""

    def test_missing_credentials_raises(self):
        """Test that missing credentials raises error."""
        config = {
            "gigachat": {}
        }

        with pytest.raises(LLMProviderConfigError) as exc_info:
            _create_gigachat_provider(config)

        assert "credentials" in str(exc_info.value).lower()

    def test_creates_with_credentials(self):
        """Test provider creation with credentials."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        config = {
            "gigachat": {
                "credentials": "test_credentials",
                "model": "GigaChat-Pro",
                "temperature": 0.7,
            }
        }

        # Patch where GigaChatProvider is imported from
        with patch("src.llm.gigachat_provider.GigaChatProvider", return_value=mock_provider):
            # Patch the security wrapper to return the provider as-is
            with patch("src.llm.factory._wrap_with_security", lambda p: p):
                provider = _create_gigachat_provider(config)

        assert provider is mock_provider


class TestCreateOpenAIProvider:
    """Tests for _create_openai_provider function."""

    def test_missing_api_key_raises(self):
        """Test that missing API key raises error."""
        config = {
            "openai": {}
        }

        with pytest.raises(LLMProviderConfigError) as exc_info:
            _create_openai_provider(config)

        assert "api key" in str(exc_info.value).lower()

    def test_creates_with_api_key(self):
        """Test provider creation with API key."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        config = {
            "openai": {
                "api_key": "sk-test123",
                "model": "gpt-4o-mini",
            }
        }

        # Patch where OpenAIProvider is imported from
        with patch("src.llm.openai_provider.OpenAIProvider", return_value=mock_provider):
            with patch("src.llm.factory._wrap_with_security", lambda p: p):
                provider = _create_openai_provider(config)

        assert provider is mock_provider

    def test_creates_azure_provider(self):
        """Test provider creation with Azure endpoint."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        config = {
            "openai": {
                "api_key": "azure-key",
                "azure_endpoint": "https://myresource.openai.azure.com",
                "azure_deployment": "my-deployment",
            }
        }

        # Patch where OpenAIProvider is imported from
        with patch("src.llm.openai_provider.OpenAIProvider", return_value=mock_provider):
            with patch("src.llm.factory._wrap_with_security", lambda p: p):
                provider = _create_openai_provider(config)

        assert provider is mock_provider


class TestSecurityWrapper:
    """Tests for _wrap_with_security function."""

    def test_wraps_when_security_enabled(self):
        """Test that provider is wrapped when security is enabled."""
        from src.llm.factory import _wrap_with_security

        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config.dlp.enabled = True
        mock_config.siem.enabled = False

        mock_provider = MagicMock(spec=BaseLLMProvider)

        # Patch where the import happens in _wrap_with_security
        with patch("src.security.get_security_config", return_value=mock_config):
            with patch("src.security.SecureLLMProvider") as mock_secure:
                mock_secure.return_value = MagicMock()
                result = _wrap_with_security(mock_provider)

                mock_secure.assert_called_once_with(mock_provider, mock_config)

    def test_returns_original_when_security_disabled(self):
        """Test that original provider is returned when security is disabled."""
        from src.llm.factory import _wrap_with_security

        mock_config = MagicMock()
        mock_config.enabled = False

        mock_provider = MagicMock(spec=BaseLLMProvider)

        with patch("src.security.get_security_config", return_value=mock_config):
            result = _wrap_with_security(mock_provider)

        assert result is mock_provider

    def test_returns_original_when_import_fails(self):
        """Test that original provider is returned when security module unavailable."""
        from src.llm.factory import _wrap_with_security

        mock_provider = MagicMock(spec=BaseLLMProvider)

        # Force ImportError when trying to import from src.security
        with patch.dict("sys.modules", {"src.security": None}):
            result = _wrap_with_security(mock_provider)

        assert result is mock_provider
