"""
Secure LLM Provider - Security wrapper for LLM providers.

Provides:
- Pre-request DLP scanning and filtering
- Post-response DLP scanning and masking
- Complete request/response logging
- SIEM event dispatch
"""

import hashlib
import logging
import time
import uuid
from typing import Any, Dict, Generator, Optional

from ..config import SecurityConfig, DLPAction, get_security_config
from ..dlp import ContentScanner, DLPBlockedException, DLPMatch, ScanResult
from ..siem import SecurityEvent, SecurityEventType, SIEMDispatcher, init_siem_dispatcher
from .request_logger import LLMSecurityLogger

logger = logging.getLogger(__name__)


class SecureLLMProvider:
    """
    Security wrapper for LLM providers.

    Wraps any BaseLLMProvider to add:
    - Pre-request DLP scanning
    - Post-response DLP filtering
    - Comprehensive audit logging
    - SIEM event dispatch

    Usage:
        from src.llm.base_provider import BaseLLMProvider
        from src.security import SecureLLMProvider, get_security_config

        # Wrap an existing provider
        base_provider = GigaChatProvider(config)
        secure_provider = SecureLLMProvider(base_provider, get_security_config())

        # Use as normal
        response = secure_provider.generate(system_prompt, user_prompt)
    """

    def __init__(
        self,
        wrapped_provider: Any,  # BaseLLMProvider
        config: Optional[SecurityConfig] = None,
    ):
        """
        Initialize secure LLM provider.

        Args:
            wrapped_provider: The underlying LLM provider to wrap
            config: Security configuration (uses global config if None)
        """
        self._wrapped = wrapped_provider
        self._config = config or get_security_config()

        # Initialize components
        self._scanner = ContentScanner(self._config.dlp) if self._config.dlp.enabled else None
        self._logger = LLMSecurityLogger(self._config) if self._config.llm_logging.enabled else None
        self._siem = init_siem_dispatcher(self._config.siem) if self._config.siem.enabled else None

        # Forward provider attributes
        self.model_name = getattr(wrapped_provider, 'model_name', 'unknown')
        self.provider_name = getattr(wrapped_provider, '__class__', type(wrapped_provider)).__name__

        logger.info(f"SecureLLMProvider initialized: scanner={self._scanner is not None}, "
                   f"logger={self._logger is not None}, siem={self._siem is not None}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> Any:  # LLMResponse
        """
        Generate response with security filtering.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            **kwargs: Additional arguments for the provider

        Returns:
            LLMResponse from the wrapped provider

        Raises:
            DLPBlockedException: If content is blocked by DLP
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract context from kwargs
        user_id = kwargs.pop('_user_id', None)
        session_id = kwargs.pop('_session_id', None)
        ip_address = kwargs.pop('_ip_address', None)

        try:
            # 1. Pre-request DLP scan
            original_system = system_prompt
            original_user = user_prompt

            if self._scanner:
                system_prompt, user_prompt = self._pre_request_filter(
                    system_prompt, user_prompt, request_id, user_id, ip_address
                )

            # 2. Call wrapped provider
            response = self._wrapped.generate(system_prompt, user_prompt, **kwargs)

            # 3. Post-response DLP scan
            if self._scanner:
                response = self._post_response_filter(response, request_id, user_id, ip_address)

            # 4. Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            tokens = getattr(response, 'metadata', {}).get('usage', {})

            # 5. Log interaction
            self._log_success(
                request_id=request_id,
                system_prompt=original_system,
                user_prompt=original_user,
                response=response,
                latency_ms=latency_ms,
                tokens=tokens,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )

            return response

        except DLPBlockedException:
            # Re-raise DLP blocks
            raise

        except Exception as e:
            # Log error
            self._log_error(
                request_id=request_id,
                error=e,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )
            raise

    def generate_simple(self, prompt: str, **kwargs) -> Any:
        """
        Generate response from a simple prompt.

        Args:
            prompt: Combined prompt
            **kwargs: Additional arguments

        Returns:
            LLMResponse from the wrapped provider
        """
        return self.generate("", prompt, **kwargs)

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> Generator:
        """
        Generate streaming response with security filtering.

        Note: Streaming responses are logged after completion.
        Pre-request filtering is applied, but post-response filtering
        requires collecting the full response.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            **kwargs: Additional arguments

        Yields:
            Chunks from the wrapped provider
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        user_id = kwargs.pop('_user_id', None)
        session_id = kwargs.pop('_session_id', None)
        ip_address = kwargs.pop('_ip_address', None)

        # Pre-request filter
        if self._scanner:
            system_prompt, user_prompt = self._pre_request_filter(
                system_prompt, user_prompt, request_id, user_id, ip_address
            )

        # Collect chunks for logging and post-filter
        chunks = []
        try:
            for chunk in self._wrapped.generate_stream(system_prompt, user_prompt, **kwargs):
                chunks.append(chunk)
                yield chunk

            # Post-process complete response
            full_response = ''.join(str(c) for c in chunks)
            if self._scanner and self._config.dlp.post_response.enabled:
                result = self._scanner.scan_response(full_response)
                if result.has_matches:
                    # Log DLP matches in response (can't modify streamed content)
                    self._dispatch_dlp_event(
                        request_id=request_id,
                        action=result.action,
                        matches=result.matches,
                        phase="response",
                        user_id=user_id,
                        ip_address=ip_address,
                    )

            # Log success
            latency_ms = (time.time() - start_time) * 1000
            self._log_stream_success(
                request_id=request_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=full_response,
                latency_ms=latency_ms,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )

        except Exception as e:
            self._log_error(
                request_id=request_id,
                error=e,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )
            raise

    def _pre_request_filter(
        self,
        system_prompt: str,
        user_prompt: str,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
    ) -> tuple:
        """
        Apply pre-request DLP filtering.

        Returns:
            Tuple of (filtered_system_prompt, filtered_user_prompt)

        Raises:
            DLPBlockedException: If content is blocked
        """
        combined = f"{system_prompt}\n{user_prompt}"
        result = self._scanner.scan_request(combined)

        if not result.has_matches:
            return system_prompt, user_prompt

        # Dispatch DLP event
        self._dispatch_dlp_event(
            request_id=request_id,
            action=result.action,
            matches=result.matches,
            phase="request",
            user_id=user_id,
            ip_address=ip_address,
        )

        if result.blocked:
            logger.warning(f"Request {request_id} blocked by DLP: {len(result.matches)} matches")
            raise DLPBlockedException(result.matches)

        if result.action == DLPAction.MASK and result.modified_content:
            # Re-split the masked content
            # This is approximate; for precise masking, scan prompts separately
            system_result = self._scanner.scan_request(system_prompt)
            user_result = self._scanner.scan_request(user_prompt)

            masked_system = system_result.modified_content or system_prompt
            masked_user = user_result.modified_content or user_prompt

            logger.info(f"Request {request_id} content masked: {len(result.matches)} patterns")
            return masked_system, masked_user

        return system_prompt, user_prompt

    def _post_response_filter(
        self,
        response: Any,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
    ) -> Any:
        """
        Apply post-response DLP filtering.

        Returns:
            Response with content potentially masked
        """
        content = getattr(response, 'content', str(response))
        result = self._scanner.scan_response(content)

        if not result.has_matches:
            return response

        # Dispatch DLP event
        self._dispatch_dlp_event(
            request_id=request_id,
            action=result.action,
            matches=result.matches,
            phase="response",
            user_id=user_id,
            ip_address=ip_address,
        )

        # Mask content in response
        if result.modified_content and hasattr(response, 'content'):
            response.content = result.modified_content
            logger.info(f"Response {request_id} content masked: {len(result.matches)} patterns")

        return response

    def _dispatch_dlp_event(
        self,
        request_id: str,
        action: DLPAction,
        matches: list,
        phase: str,
        user_id: Optional[str],
        ip_address: Optional[str],
    ) -> None:
        """Dispatch DLP event to SIEM."""
        if not self._siem:
            return

        event_type_map = {
            DLPAction.BLOCK: SecurityEventType.DLP_BLOCK,
            DLPAction.MASK: SecurityEventType.DLP_MASK,
            DLPAction.WARN: SecurityEventType.DLP_WARN,
            DLPAction.LOG_ONLY: SecurityEventType.DLP_LOG,
        }

        severity_map = {
            DLPAction.BLOCK: 3,  # Error
            DLPAction.MASK: 4,   # Warning
            DLPAction.WARN: 5,   # Notice
            DLPAction.LOG_ONLY: 6,  # Info
        }

        event = SecurityEvent.create(
            event_type=event_type_map.get(action, SecurityEventType.DLP_LOG),
            message=f"DLP {action.value}: {len(matches)} patterns in {phase}",
            request_id=request_id,
            severity=severity_map.get(action, 6),
            user_id=user_id,
            ip_address=ip_address,
            provider=self.provider_name,
            model=self.model_name,
            action=action.value,
            dlp_category=matches[0].category if matches else None,
            dlp_pattern=matches[0].pattern_name if matches else None,
            details={
                "phase": phase,
                "match_count": len(matches),
                "categories": list(set(m.category for m in matches)),
            },
        )

        self._siem.dispatch(event)

    def _log_success(
        self,
        request_id: str,
        system_prompt: str,
        user_prompt: str,
        response: Any,
        latency_ms: float,
        tokens: dict,
        user_id: Optional[str],
        session_id: Optional[str],
        ip_address: Optional[str],
    ) -> None:
        """Log successful LLM interaction."""
        if self._logger:
            self._logger.log_request(
                request_id=request_id,
                provider=self.provider_name,
                model=self.model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response=response,
                latency_ms=latency_ms,
                tokens=tokens,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )

        # SIEM event
        if self._siem:
            event = SecurityEvent.create(
                event_type=SecurityEventType.LLM_RESPONSE,
                message=f"LLM request completed: {latency_ms:.0f}ms",
                request_id=request_id,
                severity=6,  # Info
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                provider=self.provider_name,
                model=self.model_name,
                tokens_used=tokens.get('total_tokens'),
                latency_ms=latency_ms,
            )
            self._siem.dispatch(event)

    def _log_stream_success(
        self,
        request_id: str,
        system_prompt: str,
        user_prompt: str,
        response_text: str,
        latency_ms: float,
        user_id: Optional[str],
        session_id: Optional[str],
        ip_address: Optional[str],
    ) -> None:
        """Log successful streaming interaction."""
        if self._logger:
            self._logger.log_stream_request(
                request_id=request_id,
                provider=self.provider_name,
                model=self.model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=response_text,
                latency_ms=latency_ms,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )

    def _log_error(
        self,
        request_id: str,
        error: Exception,
        user_id: Optional[str],
        session_id: Optional[str],
        ip_address: Optional[str],
    ) -> None:
        """Log LLM error."""
        logger.error(f"LLM error [{request_id}]: {error}")

        if self._logger:
            self._logger.log_error(
                request_id=request_id,
                provider=self.provider_name,
                model=self.model_name,
                error=error,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
            )

        # SIEM event
        if self._siem:
            event = SecurityEvent.create(
                event_type=SecurityEventType.LLM_ERROR,
                message=f"LLM error: {str(error)[:200]}",
                request_id=request_id,
                severity=3,  # Error
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                provider=self.provider_name,
                model=self.model_name,
                details={"error_type": type(error).__name__},
            )
            self._siem.dispatch(event)

    def is_available(self) -> bool:
        """Check if underlying provider is available."""
        return self._wrapped.is_available()

    def __getattr__(self, name):
        """Forward unknown attributes to wrapped provider."""
        return getattr(self._wrapped, name)
