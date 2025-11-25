"""
Backward-Compatible LLMInterface Wrapper

Provides the same interface as the legacy src/generation/llm_interface.py
but uses the new configurable LLM provider system.

This allows existing code to work without changes while benefiting from:
- GigaChat API support
- Configurable providers via config.yaml
- Unified error handling

Usage:
    # Drop-in replacement for old LLMInterface
    from src.llm.llm_interface_compat import LLMInterface

    llm = LLMInterface()  # Uses provider from config.yaml
    response = llm.generate(system_prompt, user_prompt)  # Returns str

Author: Production Fixes - Phase 1
Date: November 25, 2025
"""

import logging
from typing import Optional, Any

from .factory import create_llm_provider
from .base_provider import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class LLMInterface:
    """
    Backward-compatible LLM interface using the new provider system.

    Provides the same API as src/generation/llm_interface.py but uses
    the configurable provider (GigaChat, local, etc.) from config.yaml.

    Key differences from old LLMInterface:
    - No model_path parameter (uses config.yaml)
    - No n_ctx, n_gpu_layers parameters (configured in yaml)
    - No grammar parameter (not supported by all providers)

    Example:
        llm = LLMInterface()

        # Chat-style generation
        response = llm.generate(
            system_prompt="You are a PostgreSQL expert",
            user_prompt="Explain MVCC"
        )
        print(response)  # str

        # Simple generation
        response = llm.generate_simple("What is PostgreSQL?")
        print(response)  # str
    """

    _global_provider: Optional[BaseLLMProvider] = None

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        """
        Initialize LLMInterface.

        Args:
            provider: Optional pre-initialized provider. If None, creates
                     one from config.yaml (uses global singleton).
        """
        if provider is not None:
            self._provider = provider
        else:
            # Use global singleton to avoid recreating provider
            if LLMInterface._global_provider is None:
                logger.info("Creating LLM provider from config.yaml")
                try:
                    LLMInterface._global_provider = create_llm_provider()
                    logger.info(f"LLM provider created: {LLMInterface._global_provider}")
                except Exception as e:
                    logger.error(f"Failed to create LLM provider: {e}")
                    raise

            self._provider = LLMInterface._global_provider

    @property
    def provider(self) -> BaseLLMProvider:
        """Get the underlying provider."""
        return self._provider

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate completion using chat format.

        Args:
            system_prompt: System instructions
            user_prompt: User input
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text (str)

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            response = self._provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.content
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise LLMProviderError(f"Generation failed: {e}") from e

    def generate_simple(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.6,
        **kwargs
    ) -> str:
        """
        Simple generation without chat formatting.

        Args:
            prompt: Direct prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text (str)

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            response = self._provider.generate_simple(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response.content
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Simple generation failed: {e}")
            raise LLMProviderError(f"Simple generation failed: {e}") from e

    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self._provider.is_available()

    @classmethod
    def reset_global_provider(cls):
        """Reset the global provider singleton (for testing)."""
        cls._global_provider = None

    def __repr__(self) -> str:
        return f"LLMInterface(provider={self._provider})"


# Convenience function
def get_llm() -> LLMInterface:
    """
    Get a configured LLMInterface instance.

    Uses global singleton, so multiple calls return the same instance.

    Returns:
        LLMInterface configured from config.yaml

    Example:
        llm = get_llm()
        response = llm.generate("You are helpful", "Hello!")
    """
    return LLMInterface()
