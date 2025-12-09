"""
LLM Security Logger - Comprehensive logging for LLM interactions.

Logs:
- Request/response details (with optional redaction)
- Token usage and latency metrics
- DLP events
- Errors
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import SecurityConfig, LLMLoggingConfig

logger = logging.getLogger("api.llm.security")


class LLMSecurityLogger:
    """
    Security-focused logger for LLM interactions.

    Features:
    - Structured JSON logging
    - Prompt redaction before logging
    - Configurable detail levels
    - Database logging (optional)
    """

    def __init__(self, config: SecurityConfig):
        """
        Initialize LLM security logger.

        Args:
            config: Security configuration
        """
        self._config = config
        self._log_config = config.llm_logging
        self._enabled = self._log_config.enabled

    def log_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response: Any,
        latency_ms: float,
        tokens: Dict[str, int],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        dlp_action: Optional[str] = None,
        dlp_matches: Optional[list] = None,
    ) -> None:
        """
        Log a complete LLM request/response.

        Args:
            request_id: Unique request identifier
            provider: LLM provider name
            model: Model name
            system_prompt: System prompt (may be redacted)
            user_prompt: User prompt (may be redacted)
            response: LLM response object
            latency_ms: Request latency in milliseconds
            tokens: Token usage dictionary
            user_id: User identifier
            session_id: Session identifier
            ip_address: Client IP address
            dlp_action: DLP action taken (if any)
            dlp_matches: DLP matches found (if any)
        """
        if not self._enabled:
            return

        log_data = self._build_log_data(
            request_id=request_id,
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
            latency_ms=latency_ms,
            tokens=tokens,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            dlp_action=dlp_action,
            dlp_matches=dlp_matches,
            status="success",
        )

        logger.info(json.dumps(log_data, ensure_ascii=False))

        # Log to database if enabled
        if self._log_config.log_to_database:
            self._log_to_database(log_data)

    def log_stream_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_text: str,
        latency_ms: float,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log a streaming LLM request."""
        if not self._enabled:
            return

        log_data = {
            "event": "llm.stream_response",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "status": "success",
            "streaming": True,
            "latency_ms": round(latency_ms, 2),
            "response_length": len(response_text),
        }

        if user_id:
            log_data["user_id"] = user_id
        if session_id:
            log_data["session_id"] = session_id
        if ip_address:
            log_data["ip_address"] = ip_address

        # Add prompts if configured
        if self._log_config.log_prompts:
            log_data["system_prompt_hash"] = self._hash_content(system_prompt)
            log_data["user_prompt_preview"] = self._truncate_and_redact(
                user_prompt, self._log_config.max_prompt_length
            )

        # Add response if configured
        if self._log_config.log_responses:
            log_data["response_preview"] = self._truncate_and_redact(
                response_text, self._log_config.max_response_length
            )

        logger.info(json.dumps(log_data, ensure_ascii=False))

    def log_error(
        self,
        request_id: str,
        provider: str,
        model: str,
        error: Exception,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Log an LLM error."""
        if not self._enabled:
            return

        log_data = {
            "event": "llm.error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],
        }

        if user_id:
            log_data["user_id"] = user_id
        if session_id:
            log_data["session_id"] = session_id
        if ip_address:
            log_data["ip_address"] = ip_address

        logger.error(json.dumps(log_data, ensure_ascii=False))

    def _build_log_data(
        self,
        request_id: str,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response: Any,
        latency_ms: float,
        tokens: Dict[str, int],
        user_id: Optional[str],
        session_id: Optional[str],
        ip_address: Optional[str],
        dlp_action: Optional[str],
        dlp_matches: Optional[list],
        status: str,
    ) -> Dict[str, Any]:
        """Build structured log data."""
        log_data = {
            "event": "llm.response",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "status": status,
        }

        # User context
        if user_id:
            log_data["user_id"] = user_id
        if session_id:
            log_data["session_id"] = session_id
        if ip_address:
            log_data["ip_address"] = ip_address

        # Prompts (redacted if configured)
        if self._log_config.log_prompts:
            log_data["system_prompt_hash"] = self._hash_content(system_prompt)
            log_data["system_prompt_length"] = len(system_prompt)

            if self._log_config.redact_prompts:
                log_data["user_prompt_preview"] = self._truncate_and_redact(
                    user_prompt, self._log_config.max_prompt_length
                )
            else:
                log_data["user_prompt_preview"] = user_prompt[:self._log_config.max_prompt_length]

            log_data["user_prompt_length"] = len(user_prompt)

        # Response
        if self._log_config.log_responses:
            response_content = getattr(response, 'content', str(response))
            log_data["response_preview"] = self._truncate_and_redact(
                response_content, self._log_config.max_response_length
            )
            log_data["response_length"] = len(response_content)

        # Metrics
        if self._log_config.log_latency:
            log_data["latency_ms"] = round(latency_ms, 2)

        if self._log_config.log_token_usage and tokens:
            log_data["prompt_tokens"] = tokens.get("prompt_tokens")
            log_data["completion_tokens"] = tokens.get("completion_tokens")
            log_data["total_tokens"] = tokens.get("total_tokens")

        # DLP info
        if dlp_action:
            log_data["dlp_action"] = dlp_action
        if dlp_matches:
            log_data["dlp_match_count"] = len(dlp_matches)
            log_data["dlp_categories"] = list(set(m.category for m in dlp_matches))

        return log_data

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _truncate_and_redact(self, content: str, max_length: int) -> str:
        """Truncate content and apply basic redaction."""
        if not content:
            return ""

        # Truncate
        if len(content) > max_length:
            content = content[:max_length] + "..."

        # Basic redaction (if configured)
        if self._log_config.redact_prompts:
            # These patterns should match common sensitive data
            # More sophisticated redaction happens in DLP scanner
            import re
            # Redact potential API keys
            content = re.sub(
                r'(["\']?)(api[_-]?key|password|secret|token)(["\']?\s*[:=]\s*["\']?)([^\s"\']+)',
                r'\1\2\3[REDACTED]',
                content,
                flags=re.IGNORECASE
            )

        return content

    def _log_to_database(self, log_data: Dict[str, Any]) -> None:
        """
        Log to database (if available).

        This is a placeholder - actual implementation depends on
        database availability and schema.
        """
        try:
            # Import here to avoid circular dependency
            # and gracefully handle missing database
            pass  # Database logging will be implemented separately
        except Exception as e:
            logger.debug(f"Database logging not available: {e}")
