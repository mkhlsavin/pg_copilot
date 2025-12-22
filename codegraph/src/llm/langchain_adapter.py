"""
LangChain Adapter for LLM Providers

Adapter to make our BaseLLMProvider compatible with LangChain and RAGAS.
RAGAS evaluation metrics require LangChain-compatible LLM instances.

Author: Configurable LLM Architecture - Week 2
Date: November 25, 2025
"""

import logging
from typing import Any, List, Optional, Mapping

from langchain_core.language_models.llms import LLM as LangChainLLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from .base_provider import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class LangChainLLMAdapter(LangChainLLM):
    """
    Adapter to make BaseLLMProvider compatible with LangChain.

    This adapter wraps our custom LLM providers (LocalLLMProvider, etc.)
    and exposes them as LangChain LLM instances, which are required by RAGAS.

    Example:
        # Wrap LocalLLMProvider for RAGAS
        from src.llm import create_llm_provider
        from src.llm.langchain_adapter import LangChainLLMAdapter

        provider = create_llm_provider()  # LocalLLMProvider
        langchain_llm = LangChainLLMAdapter(provider)

        # Use with RAGAS
        from ragas import evaluate
        results = evaluate(dataset, llm=langchain_llm)
    """

    provider: BaseLLMProvider
    """The underlying LLM provider"""

    def __init__(self, provider: BaseLLMProvider, **kwargs: Any):
        """
        Initialize adapter with a BaseLLMProvider.

        Args:
            provider: Our custom LLM provider (LocalLLMProvider, etc.)
            **kwargs: Additional LangChain LLM parameters
        """
        super().__init__(**kwargs)
        self.provider = provider
        logger.info(f"Created LangChain adapter for {provider.__class__.__name__}")

    @property
    def _llm_type(self) -> str:
        """Return type of LLM."""
        return f"custom_{self.provider.__class__.__name__.lower()}"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call the LLM with a prompt and return the response.

        This is the main method that LangChain and RAGAS will call.

        Args:
            prompt: The prompt to send to the LLM
            stop: Optional list of stop sequences
            run_manager: LangChain callback manager (unused)
            **kwargs: Additional generation parameters

        Returns:
            Generated text response
        """
        try:
            # Use generate_simple for direct prompt (RAGAS typically sends single prompts)
            response: LLMResponse = self.provider.generate_simple(
                prompt=prompt,
                stop=stop,
                **kwargs
            )

            return response.content

        except Exception as e:
            logger.error(f"LangChain adapter call failed: {e}")
            raise

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """
        Return identifying parameters for the LLM.

        Used by LangChain for caching and tracking.
        """
        return {
            "provider_type": self.provider.__class__.__name__,
            "model_info": getattr(self.provider, 'model_path', None) or
                         getattr(self.provider, 'model_name', 'unknown'),
        }


def create_langchain_adapter(provider: BaseLLMProvider) -> LangChainLLM:
    """
    Factory function to create a LangChain adapter from any BaseLLMProvider.

    Args:
        provider: Any BaseLLMProvider instance (LocalLLMProvider, etc.)

    Returns:
        LangChain-compatible LLM instance

    Example:
        from src.llm import create_llm_provider
        from src.llm.langchain_adapter import create_langchain_adapter

        # For local model
        provider = create_llm_provider()  # Uses config.yaml
        langchain_llm = create_langchain_adapter(provider)

        # For GigaChat (already LangChain-compatible)
        from src.llm.gigachat_provider import GigaChatProvider
        gigachat = GigaChatProvider(config)

        # GigaChatProvider.client is already a LangChain GigaChat instance,
        # so we can use it directly without adapter
        langchain_llm = gigachat.client
    """
    # Check if provider is already LangChain-compatible
    # GigaChatProvider has a .client attribute that is a LangChain GigaChat instance
    if hasattr(provider, 'client') and isinstance(provider.client, LangChainLLM):
        logger.info(f"{provider.__class__.__name__} is already LangChain-compatible, using .client directly")
        return provider.client

    # Otherwise, wrap it with our adapter
    return LangChainLLMAdapter(provider)


def get_ragas_llm(provider: Optional[BaseLLMProvider] = None) -> LangChainLLM:
    """
    Get a LangChain-compatible LLM for RAGAS evaluation.

    Args:
        provider: Optional BaseLLMProvider. If None, creates from config.yaml.

    Returns:
        LangChain-compatible LLM instance ready for RAGAS

    Example:
        # Use default provider from config.yaml
        from src.llm.langchain_adapter import get_ragas_llm
        llm = get_ragas_llm()

        # Use specific provider
        from src.llm import create_llm_provider, LLMConfig
        custom_config = LLMConfig(...)
        provider = create_llm_provider(custom_config)
        llm = get_ragas_llm(provider)
    """
    if provider is None:
        # Create provider from config.yaml
        from .factory import create_llm_provider
        provider = create_llm_provider()
        logger.info("Created default LLM provider for RAGAS from config.yaml")

    return create_langchain_adapter(provider)
