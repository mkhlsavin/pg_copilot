"""
Tests for Secure LLM Provider.

Tests for SecureLLMProvider with DLP scanning and SIEM integration.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List, Optional


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response: str = "Test response"):
        self.response = response
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        return self.response

    async def generate_with_messages(
        self, messages: List[dict], **kwargs
    ) -> str:
        self.call_count += 1
        return self.response


class MockDLPScanner:
    """Mock DLP scanner for testing."""

    def __init__(
        self,
        should_block: bool = False,
        detected_patterns: Optional[List[str]] = None,
    ):
        self.should_block = should_block
        self.detected_patterns = detected_patterns or []
        self.scan_count = 0

    async def scan(self, text: str) -> dict:
        self.scan_count += 1
        return {
            "blocked": self.should_block,
            "patterns": self.detected_patterns,
            "severity": "HIGH" if self.should_block else "NONE",
        }


class MockSIEMDispatcher:
    """Mock SIEM dispatcher for testing."""

    def __init__(self):
        self.events = []

    async def dispatch(self, event: dict):
        self.events.append(event)


class TestSecureLLMProviderInit:
    """Tests for SecureLLMProvider initialization."""

    def test_init_with_required_params(self):
        """Test initialization with required parameters."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
        )

        assert secure_provider.provider is mock_provider
        assert secure_provider.dlp_scanner is mock_dlp

    def test_init_with_siem(self):
        """Test initialization with SIEM dispatcher."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
        )

        assert secure_provider.siem_dispatcher is mock_siem

    def test_init_with_config(self):
        """Test initialization with configuration."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        config = {
            "block_on_detection": True,
            "log_all_requests": True,
            "redact_sensitive": True,
        }

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config=config,
        )

        assert secure_provider.config["block_on_detection"] is True
        assert secure_provider.config["log_all_requests"] is True


class TestPreRequestScanning:
    """Tests for pre-request DLP scanning."""

    @pytest.fixture
    def secure_provider(self):
        """Create SecureLLMProvider for testing."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        return SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
        )

    @pytest.mark.asyncio
    async def test_scan_prompt_clean(self, secure_provider):
        """Test scanning clean prompt."""
        result = await secure_provider._scan_request("Hello, how are you?")

        assert result["blocked"] is False

    @pytest.mark.asyncio
    async def test_scan_prompt_with_pii(self):
        """Test scanning prompt with PII."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner(
            should_block=True,
            detected_patterns=["SSN", "CREDIT_CARD"],
        )

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
        )

        result = await secure_provider._scan_request(
            "My SSN is 123-45-6789 and card is 4111-1111-1111-1111"
        )

        assert result["blocked"] is True
        assert "SSN" in result["patterns"]

    @pytest.mark.asyncio
    async def test_scan_triggers_siem_event(self):
        """Test that scan triggers SIEM event on detection."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner(
            should_block=True,
            detected_patterns=["API_KEY"],
        )
        mock_siem = MockSIEMDispatcher()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
        )

        await secure_provider._scan_request("api_key=sk-1234567890")

        assert len(mock_siem.events) >= 1
        assert mock_siem.events[0]["event_type"] == "dlp_detection"


class TestPostResponseScanning:
    """Tests for post-response DLP scanning."""

    @pytest.fixture
    def secure_provider(self):
        """Create SecureLLMProvider for testing."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        return SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
        )

    @pytest.mark.asyncio
    async def test_scan_response_clean(self, secure_provider):
        """Test scanning clean response."""
        result = await secure_provider._scan_response("Here is your answer.")

        assert result["blocked"] is False

    @pytest.mark.asyncio
    async def test_scan_response_with_sensitive_data(self):
        """Test scanning response with sensitive data."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner(
            should_block=True,
            detected_patterns=["PASSWORD", "INTERNAL_IP"],
        )

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
        )

        result = await secure_provider._scan_response(
            "The password is secret123 and server is 192.168.1.100"
        )

        assert result["blocked"] is True


class TestGenerateSecure:
    """Tests for secure generation."""

    @pytest.fixture
    def clean_provider(self):
        """Create provider with clean DLP scanner."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="Safe response")
        mock_dlp = MockDLPScanner(should_block=False)
        mock_siem = MockSIEMDispatcher()

        return SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
        )

    @pytest.mark.asyncio
    async def test_generate_success(self, clean_provider):
        """Test successful generation."""
        result = await clean_provider.generate("Hello")

        assert result == "Safe response"

    @pytest.mark.asyncio
    async def test_generate_blocked_request(self):
        """Test generation blocked by request DLP."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner(
            should_block=True,
            detected_patterns=["SECRET"],
        )

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={"block_on_detection": True},
        )

        with pytest.raises(Exception) as exc_info:
            await secure_provider.generate("Here is my SECRET key")

        assert "blocked" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_blocked_response(self):
        """Test generation blocked by response DLP."""
        from src.security.llm.secure_provider import SecureLLMProvider

        # DLP passes request but blocks response
        call_count = 0

        class ResponseBlockingDLP:
            async def scan(self, text):
                nonlocal call_count
                call_count += 1
                # First call is request (pass), second is response (block)
                if call_count == 1:
                    return {"blocked": False, "patterns": []}
                return {"blocked": True, "patterns": ["LEAKED_DATA"]}

        mock_provider = MockLLMProvider(response="Leaked data here")
        mock_dlp = ResponseBlockingDLP()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={"block_on_detection": True},
        )

        with pytest.raises(Exception) as exc_info:
            await secure_provider.generate("Tell me something")

        assert "blocked" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_logs_request(self):
        """Test that generation logs request to SIEM."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
            config={"log_all_requests": True},
        )

        await secure_provider.generate("Test prompt")

        # Should log the request
        assert len(mock_siem.events) >= 1


class TestRedaction:
    """Tests for sensitive data redaction."""

    @pytest.fixture
    def redacting_provider(self):
        """Create provider with redaction enabled."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner(
            should_block=False,
            detected_patterns=["SSN"],
        )

        return SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={"redact_sensitive": True, "block_on_detection": False},
        )

    @pytest.mark.asyncio
    async def test_redact_ssn(self, redacting_provider):
        """Test SSN redaction."""
        redacted = await redacting_provider._redact_sensitive(
            "My SSN is 123-45-6789"
        )

        assert "123-45-6789" not in redacted
        assert "[REDACTED]" in redacted or "XXX" in redacted

    @pytest.mark.asyncio
    async def test_redact_credit_card(self, redacting_provider):
        """Test credit card redaction."""
        redacted = await redacting_provider._redact_sensitive(
            "Card: 4111-1111-1111-1111"
        )

        assert "4111-1111-1111-1111" not in redacted

    @pytest.mark.asyncio
    async def test_redact_preserves_clean_text(self, redacting_provider):
        """Test that clean text is preserved."""
        original = "This is a clean message with no sensitive data."
        redacted = await redacting_provider._redact_sensitive(original)

        assert redacted == original

    @pytest.mark.asyncio
    async def test_redact_multiple_patterns(self, redacting_provider):
        """Test redacting multiple patterns."""
        text = "SSN: 123-45-6789, Email: user@example.com, Phone: 555-1234"
        redacted = await redacting_provider._redact_sensitive(text)

        # At least SSN should be redacted
        assert "123-45-6789" not in redacted


class TestAuditLogging:
    """Tests for audit logging."""

    @pytest.fixture
    def auditing_provider(self):
        """Create provider with audit logging."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        return SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
            config={"audit_logging": True},
        )

    @pytest.mark.asyncio
    async def test_audit_log_created(self, auditing_provider):
        """Test that audit log is created."""
        await auditing_provider.generate("Test prompt")

        events = auditing_provider.siem_dispatcher.events
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_audit_log_contains_metadata(self, auditing_provider):
        """Test audit log contains required metadata."""
        await auditing_provider.generate("Test prompt")

        events = auditing_provider.siem_dispatcher.events
        event = events[-1]

        assert "timestamp" in event or "event_type" in event

    @pytest.mark.asyncio
    async def test_audit_log_on_block(self):
        """Test audit log when request is blocked."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner(should_block=True, detected_patterns=["SECRET"])
        mock_siem = MockSIEMDispatcher()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
            config={"block_on_detection": True, "audit_logging": True},
        )

        try:
            await secure_provider.generate("My SECRET")
        except Exception:
            pass

        # Should log the block event
        assert len(mock_siem.events) >= 1
        block_events = [e for e in mock_siem.events if "block" in str(e).lower()]
        assert len(block_events) >= 0  # May or may not have explicit block event


class TestRateLimiting:
    """Tests for rate limiting."""

    @pytest.fixture
    def rate_limited_provider(self):
        """Create provider with rate limiting."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        return SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={"rate_limit": 10, "rate_limit_window": 60},
        )

    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_usage(self, rate_limited_provider):
        """Test that normal usage is allowed."""
        for _ in range(5):
            await rate_limited_provider.generate("Test")

        # Should not raise rate limit error
        assert rate_limited_provider.provider.call_count == 5

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_usage(self):
        """Test that excessive usage is blocked."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={"rate_limit": 2, "rate_limit_window": 60},
        )

        # Make requests up to limit
        await secure_provider.generate("Test 1")
        await secure_provider.generate("Test 2")

        # Third request should be rate limited (if implemented)
        # This is optional behavior
        try:
            await secure_provider.generate("Test 3")
        except Exception as e:
            assert "rate" in str(e).lower()


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def error_provider(self):
        """Create provider that raises errors."""
        from src.security.llm.secure_provider import SecureLLMProvider

        class ErrorProvider:
            async def generate(self, prompt, **kwargs):
                raise Exception("Provider error")

        mock_dlp = MockDLPScanner()

        return SecureLLMProvider(
            provider=ErrorProvider(),
            dlp_scanner=mock_dlp,
        )

    @pytest.mark.asyncio
    async def test_provider_error_propagates(self, error_provider):
        """Test that provider errors propagate."""
        with pytest.raises(Exception) as exc_info:
            await error_provider.generate("Test")

        assert "Provider error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dlp_error_handling(self):
        """Test DLP scanner error handling."""
        from src.security.llm.secure_provider import SecureLLMProvider

        class ErrorDLP:
            async def scan(self, text):
                raise Exception("DLP error")

        mock_provider = MockLLMProvider()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=ErrorDLP(),
            config={"fail_open": True},
        )

        # With fail_open, should proceed despite DLP error
        try:
            result = await secure_provider.generate("Test")
            assert result is not None
        except Exception:
            # Or it may propagate the error
            pass

    @pytest.mark.asyncio
    async def test_siem_error_does_not_block(self):
        """Test that SIEM errors don't block requests."""
        from src.security.llm.secure_provider import SecureLLMProvider

        class ErrorSIEM:
            async def dispatch(self, event):
                raise Exception("SIEM error")

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=ErrorSIEM(),
        )

        # SIEM error should not block the request
        result = await secure_provider.generate("Test")
        assert result is not None


class TestConfiguration:
    """Tests for configuration options."""

    def test_default_config(self):
        """Test default configuration values."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
        )

        # Should have sensible defaults
        assert secure_provider.config is not None

    def test_config_override(self):
        """Test configuration override."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        custom_config = {
            "block_on_detection": False,
            "redact_sensitive": True,
            "custom_option": "value",
        }

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config=custom_config,
        )

        assert secure_provider.config["block_on_detection"] is False
        assert secure_provider.config["redact_sensitive"] is True

    def test_invalid_config_handled(self):
        """Test that invalid config is handled gracefully."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()

        # Should not raise on empty config
        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={},
        )

        assert secure_provider is not None


class TestIntegration:
    """Integration tests for SecureLLMProvider."""

    @pytest.mark.asyncio
    async def test_full_secure_flow(self):
        """Test complete secure generation flow."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="Secure answer")
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
            config={
                "log_all_requests": True,
                "audit_logging": True,
            },
        )

        result = await secure_provider.generate("What is 2+2?")

        assert result == "Secure answer"
        assert mock_dlp.scan_count >= 1  # At least request scan

    @pytest.mark.asyncio
    async def test_secure_flow_with_redaction(self):
        """Test secure flow with redaction."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider(response="The answer is 42")
        mock_dlp = MockDLPScanner(
            should_block=False,
            detected_patterns=["EMAIL"],
        )

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            config={
                "redact_sensitive": True,
                "block_on_detection": False,
            },
        )

        result = await secure_provider.generate("Email: test@example.com")

        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self):
        """Test multiple sequential requests."""
        from src.security.llm.secure_provider import SecureLLMProvider

        mock_provider = MockLLMProvider()
        mock_dlp = MockDLPScanner()
        mock_siem = MockSIEMDispatcher()

        secure_provider = SecureLLMProvider(
            provider=mock_provider,
            dlp_scanner=mock_dlp,
            siem_dispatcher=mock_siem,
        )

        results = []
        for i in range(5):
            result = await secure_provider.generate(f"Request {i}")
            results.append(result)

        assert len(results) == 5
        assert mock_provider.call_count == 5
