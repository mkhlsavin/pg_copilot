"""
Tests for Secure LLM Provider.

Tests for SecureLLMProvider with DLP scanning and SIEM integration.
Updated to match current API signature.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List, Optional


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response: str = "Test response"):
        self.response = response
        self.call_count = 0
        self.model_name = "mock-model"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> MagicMock:
        """Mock generate method matching expected signature."""
        self.call_count += 1
        mock_response = MagicMock()
        mock_response.content = self.response
        mock_response.metadata = {"usage": {"total_tokens": 100}}
        return mock_response

    def generate_stream(self, system_prompt: str, user_prompt: str, **kwargs):
        """Mock streaming generate method."""
        self.call_count += 1
        yield self.response

    def is_available(self) -> bool:
        return True


class MockSecurityConfig:
    """Mock SecurityConfig for testing."""

    def __init__(
        self,
        dlp_enabled: bool = False,
        logging_enabled: bool = False,
        siem_enabled: bool = False,
    ):
        # DLP config
        self.dlp = MagicMock()
        self.dlp.enabled = dlp_enabled
        self.dlp.pre_request = MagicMock()
        self.dlp.pre_request.enabled = dlp_enabled
        self.dlp.post_response = MagicMock()
        self.dlp.post_response.enabled = dlp_enabled

        # Logging config
        self.llm_logging = MagicMock()
        self.llm_logging.enabled = logging_enabled

        # SIEM config
        self.siem = MagicMock()
        self.siem.enabled = siem_enabled


class TestSecureLLMProviderInit:
    """Tests for SecureLLMProvider initialization."""

    def test_init_with_provider_only(self):
        """Test initialization with provider only (default config)."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()

        with patch('src.security.llm.secure_provider.get_security_config') as mock_config:
            mock_config.return_value = MockSecurityConfig()

            secure_provider = SecureLLMProvider(
                wrapped_provider=mock_provider,
            )

            assert secure_provider._wrapped is mock_provider

    def test_init_with_custom_config(self):
        """Test initialization with custom SecurityConfig."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig(dlp_enabled=True)

        secure_provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        assert secure_provider._config is mock_config

    def test_init_sets_model_name(self):
        """Test that model_name is forwarded from provider."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_provider.model_name = "test-model"

        with patch('src.security.llm.secure_provider.get_security_config') as mock_config:
            mock_config.return_value = MockSecurityConfig()

            secure_provider = SecureLLMProvider(
                wrapped_provider=mock_provider,
            )

            assert secure_provider.model_name == "test-model"


class TestSecureGeneration:
    """Tests for secure generation."""

    @pytest.fixture
    def secure_provider(self):
        """Create SecureLLMProvider for testing."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="Safe response")
        mock_config = MockSecurityConfig()

        return SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

    def test_generate_success(self, secure_provider):
        """Test successful generation."""
        result = secure_provider.generate("System prompt", "User prompt")

        assert result.content == "Safe response"

    def test_generate_calls_wrapped_provider(self, secure_provider):
        """Test that generate calls the wrapped provider."""
        secure_provider.generate("System", "User")

        assert secure_provider._wrapped.call_count == 1

    def test_generate_simple(self, secure_provider):
        """Test generate_simple method."""
        result = secure_provider.generate_simple("Simple prompt")

        assert result.content == "Safe response"

    def test_is_available_forwards_to_wrapped(self, secure_provider):
        """Test is_available forwards to wrapped provider."""
        assert secure_provider.is_available() is True


class TestDLPScanning:
    """Tests for DLP scanning integration."""

    @pytest.fixture
    def dlp_enabled_provider(self):
        """Create provider with DLP enabled."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="Safe response")
        mock_config = MockSecurityConfig(dlp_enabled=True)

        with patch('src.security.llm.secure_provider.ContentScanner') as mock_scanner_class:
            mock_scanner = MagicMock()
            # Return clean scan result
            mock_result = MagicMock()
            mock_result.has_matches = False
            mock_result.blocked = False
            mock_scanner.scan_request.return_value = mock_result
            mock_scanner.scan_response.return_value = mock_result
            mock_scanner_class.return_value = mock_scanner

            provider = SecureLLMProvider(
                wrapped_provider=mock_provider,
                config=mock_config,
            )
            provider._test_scanner = mock_scanner  # For test access
            return provider

    def test_dlp_scanner_initialized_when_enabled(self, dlp_enabled_provider):
        """Test that DLP scanner is initialized when enabled."""
        assert dlp_enabled_provider._scanner is not None

    def test_clean_request_passes(self, dlp_enabled_provider):
        """Test that clean request passes through."""
        result = dlp_enabled_provider.generate("System", "User prompt")

        assert result.content == "Safe response"


class TestDLPBlocking:
    """Tests for DLP blocking behavior."""

    def test_blocked_request_raises_exception(self):
        """Test that blocked request raises DLPBlockedException."""
        from src.security.llm.secure_provider import SecureLLMProvider
        from src.security.dlp import DLPBlockedException, DLPMatch
        from src.security.dlp.patterns import MatchType
        from src.security.config import DLPAction

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig(dlp_enabled=True)

        with patch('src.security.llm.secure_provider.ContentScanner') as mock_scanner_class:
            mock_scanner = MagicMock()
            mock_result = MagicMock()
            mock_result.has_matches = True
            mock_result.blocked = True
            # Create proper DLPMatch object with required fields
            mock_match = DLPMatch(
                category="PII",
                pattern_name="SSN",
                match_type=MatchType.REGEX,
                matched_text="123-45-6789",
                start=0,
                end=11,
                action=DLPAction.BLOCK,
            )
            mock_result.matches = [mock_match]
            mock_scanner.scan_request.return_value = mock_result
            mock_scanner_class.return_value = mock_scanner

            provider = SecureLLMProvider(
                wrapped_provider=mock_provider,
                config=mock_config,
            )

            with pytest.raises(DLPBlockedException):
                provider.generate("System", "Sensitive content")


class TestLogging:
    """Tests for logging integration."""

    def test_logger_initialized_when_enabled(self):
        """Test that logger is initialized when enabled."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig(logging_enabled=True)

        with patch('src.security.llm.secure_provider.LLMSecurityLogger') as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger_class.return_value = mock_logger

            provider = SecureLLMProvider(
                wrapped_provider=mock_provider,
                config=mock_config,
            )

            assert provider._logger is not None

    def test_logger_not_initialized_when_disabled(self):
        """Test that logger is not initialized when disabled."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig(logging_enabled=False)

        provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        assert provider._logger is None


class TestSIEMIntegration:
    """Tests for SIEM integration."""

    def test_siem_initialized_when_enabled(self):
        """Test that SIEM dispatcher is initialized when enabled."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig(siem_enabled=True)

        with patch('src.security.llm.secure_provider.init_siem_dispatcher') as mock_init:
            mock_siem = MagicMock()
            mock_init.return_value = mock_siem

            provider = SecureLLMProvider(
                wrapped_provider=mock_provider,
                config=mock_config,
            )

            assert provider._siem is not None

    def test_siem_not_initialized_when_disabled(self):
        """Test that SIEM is not initialized when disabled."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig(siem_enabled=False)

        provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        assert provider._siem is None


class TestErrorHandling:
    """Tests for error handling."""

    def test_provider_error_propagates(self):
        """Test that provider errors propagate."""
        from src.security.llm.secure_provider import SecureLLMProvider

        class ErrorProvider:
            model_name = "error-model"

            def generate(self, system_prompt, user_prompt, **kwargs):
                raise Exception("Provider error")

            def is_available(self):
                return True

        mock_config = MockSecurityConfig()

        provider = SecureLLMProvider(
            wrapped_provider=ErrorProvider(),
            config=mock_config,
        )

        with pytest.raises(Exception) as exc_info:
            provider.generate("System", "User")

        assert "Provider error" in str(exc_info.value)


class TestAttributeForwarding:
    """Tests for attribute forwarding to wrapped provider."""

    def test_unknown_attribute_forwarded(self):
        """Test that unknown attributes are forwarded to wrapped provider."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_provider.custom_attribute = "custom_value"
        mock_config = MockSecurityConfig()

        provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        assert provider.custom_attribute == "custom_value"


class TestStreaming:
    """Tests for streaming generation."""

    def test_generate_stream(self):
        """Test streaming generation."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="Streamed")
        mock_config = MockSecurityConfig()

        provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        chunks = list(provider.generate_stream("System", "User"))

        assert len(chunks) >= 1


class TestIntegration:
    """Integration tests for SecureLLMProvider."""

    def test_full_secure_flow_no_dlp(self):
        """Test complete secure generation flow without DLP."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="Secure answer")
        mock_config = MockSecurityConfig()

        provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        result = provider.generate("You are a helper", "What is 2+2?")

        assert result.content == "Secure answer"
        assert mock_provider.call_count == 1

    def test_multiple_sequential_requests(self):
        """Test multiple sequential requests."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_config = MockSecurityConfig()

        provider = SecureLLMProvider(
            wrapped_provider=mock_provider,
            config=mock_config,
        )

        results = []
        for i in range(5):
            result = provider.generate("System", f"Request {i}")
            results.append(result)

        assert len(results) == 5
        assert mock_provider.call_count == 5
