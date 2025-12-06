"""
Local LLM Provider

Provider for local LLM models using llama-cpp-python.
Refactored from src/generation/llm_interface.py to use BaseLLMProvider interface.

Author: Configurable LLM Architecture
Date: November 25, 2025
"""

import logging
import os
from typing import Optional
from pathlib import Path

from llama_cpp import Llama, LlamaGrammar

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderNotAvailableError,
)

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    """
    Local LLM provider using llama-cpp-python.

    Supports:
    - GGUF models (llama.cpp format)
    - GPU acceleration (CUDA, Metal)
    - Grammar-constrained generation
    - ChatML format for chat models

    Example:
        config = LLMConfig(
            provider_type='local',
            temperature=0.7,
            max_tokens=512,
            extra_params={
                'model_path': '/path/to/model.gguf',
                'n_ctx': 8192,
                'n_gpu_layers': -1
            }
        )

        provider = LocalLLMProvider(config)
        response = provider.generate(
            system_prompt="You are a code analyst",
            user_prompt="Explain this code: ...",
        )
        print(response.content)
    """

    # Model paths from environment variables or config
    # Set LLMXCPG_MODEL_PATH or QWEN3_MODEL_PATH environment variables
    # or provide model_path in config.extra_params
    DEFAULT_LLMXCPG_MODEL = os.environ.get('LLMXCPG_MODEL_PATH')
    DEFAULT_QWEN3_MODEL = os.environ.get('QWEN3_MODEL_PATH')

    def __init__(self, config: LLMConfig):
        """
        Initialize local LLM provider.

        Args:
            config: LLMConfig with extra_params containing:
                - model_path: Path to GGUF model file
                - use_llmxcpg: Use fine-tuned LLMxCPG model (default: True)
                - n_ctx: Context window size (default: 8192)
                - n_gpu_layers: GPU layers, -1 = all (default: -1)
                - n_batch: Batch size (default: 512)
                - n_threads: CPU threads (default: 8)
                - verbose: Enable verbose logging (default: False)
        """
        super().__init__(config)

        # Извлечение параметров из extra_params
        params = config.extra_params or {}

        self.model_path = params.get('model_path')
        self.use_llmxcpg = params.get('use_llmxcpg', True)
        self.n_ctx = params.get('n_ctx', 8192)
        self.n_gpu_layers = params.get('n_gpu_layers', -1)
        self.n_batch = params.get('n_batch', 512)
        self.n_threads = params.get('n_threads', 8)
        self.verbose = params.get('verbose', False)

        # Выбор модели
        if self.model_path is None:
            if self.use_llmxcpg:
                self.model_path = self.DEFAULT_LLMXCPG_MODEL
                if self.model_path:
                    logger.info("Using LLMxCPG-Q model (fine-tuned for CPGQL)")
            else:
                self.model_path = self.DEFAULT_QWEN3_MODEL
                if self.model_path:
                    logger.info("Using Qwen3-Coder-32B model (general coder)")

            if self.model_path is None:
                logger.error(
                    "No model path specified. Set LLMXCPG_MODEL_PATH or QWEN3_MODEL_PATH "
                    "environment variable, or provide model_path in config.extra_params"
                )
                self.model = None
                self._initialized = False
                return

        # Проверка существования модели
        if not Path(self.model_path).exists():
            logger.error(f"Model file not found: {self.model_path}")
            self.model = None
            self._initialized = False
            return

        # Загрузка модели
        try:
            logger.info(f"Loading model: {self.model_path}")
            logger.info(f"Context size: {self.n_ctx}, GPU layers: {self.n_gpu_layers}")

            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=self.n_batch,
                n_threads=self.n_threads,
                verbose=self.verbose
            )

            self._initialized = True
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None
            self._initialized = False

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using ChatML format.

        Args:
            system_prompt: System instructions
            user_prompt: User input
            **kwargs: Optional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated text

        Raises:
            LLMProviderNotAvailableError: If model not initialized
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError(
                "Local LLM provider not initialized. Check model_path and llama-cpp-python."
            )

        # Объединение конфигурации с параметрами вызова
        params = self._merge_config(**kwargs)

        # Получение grammar если передана
        grammar = kwargs.get('grammar')

        # Построение ChatML промпта
        prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
"""

        # Stop sequences
        stop = kwargs.get('stop', ["<|im_end|>", "<|endoftext|>"])

        logger.debug(
            f"Generating: temp={params['temperature']}, "
            f"max_tokens={params['max_tokens']}, "
            f"grammar={'enabled' if grammar else 'disabled'}"
        )

        # Генерация
        response = self.model(
            prompt,
            max_tokens=params['max_tokens'],
            temperature=params['temperature'],
            top_p=params.get('top_p', 0.9),
            top_k=params.get('top_k', 40),
            stop=stop,
            echo=False,
            grammar=grammar
        )

        content = response['choices'][0]['text'].strip()

        # Метаданные
        metadata = {
            'model_path': self.model_path,
            'usage': {
                'prompt_tokens': response.get('usage', {}).get('prompt_tokens', 0),
                'completion_tokens': response.get('usage', {}).get('completion_tokens', 0),
            },
            'finish_reason': response['choices'][0].get('finish_reason', 'stop'),
        }

        return LLMResponse(content=content, metadata=metadata)

    def generate_simple(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        Simple generation without ChatML formatting.

        Используется для CPGQL queries и других задач без chat format.

        Args:
            prompt: Direct prompt text
            **kwargs: Optional parameters

        Returns:
            LLMResponse with generated text

        Raises:
            LLMProviderNotAvailableError: If model not initialized
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError(
                "Local LLM provider not initialized. Check model_path and llama-cpp-python."
            )

        # Объединение конфигурации с параметрами вызова
        params = self._merge_config(**kwargs)

        # Получение grammar если передана
        grammar = kwargs.get('grammar')

        logger.debug(
            f"Simple generation: temp={params['temperature']}, "
            f"max_tokens={params['max_tokens']}, "
            f"grammar={'enabled' if grammar else 'disabled'}"
        )

        # Генерация
        response = self.model(
            prompt,
            max_tokens=params['max_tokens'],
            temperature=params['temperature'],
            echo=False,
            grammar=grammar
        )

        content = response['choices'][0]['text'].strip()

        # Метаданные
        metadata = {
            'model_path': self.model_path,
            'usage': {
                'prompt_tokens': response.get('usage', {}).get('prompt_tokens', 0),
                'completion_tokens': response.get('usage', {}).get('completion_tokens', 0),
            },
            'finish_reason': response['choices'][0].get('finish_reason', 'stop'),
        }

        return LLMResponse(content=content, metadata=metadata)

    def is_available(self) -> bool:
        """
        Check if local LLM provider is ready.

        Returns:
            True if model loaded successfully, False otherwise
        """
        return self._initialized and self.model is not None

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ):
        """
        Streaming generation (опционально для локальной модели).

        Args:
            system_prompt: System instructions
            user_prompt: User input
            **kwargs: Optional parameters

        Yields:
            Chunks of generated text
        """
        if not self.is_available():
            raise LLMProviderNotAvailableError(
                "Local LLM provider not initialized"
            )

        # Построение ChatML промпта
        prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
"""

        params = self._merge_config(**kwargs)
        stop = kwargs.get('stop', ["<|im_end|>", "<|endoftext|>"])

        # Streaming generation
        stream = self.model(
            prompt,
            max_tokens=params['max_tokens'],
            temperature=params['temperature'],
            top_p=params.get('top_p', 0.9),
            top_k=params.get('top_k', 40),
            stop=stop,
            echo=False,
            stream=True  # Enable streaming
        )

        for chunk in stream:
            text = chunk['choices'][0]['text']
            if text:
                yield text

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            logger.debug("Local LLM model cleanup")

    def __repr__(self) -> str:
        model_name = Path(self.model_path).name if self.model_path else "unknown"
        return (
            f"LocalLLMProvider("
            f"model='{model_name}', "
            f"initialized={self._initialized}, "
            f"n_ctx={self.n_ctx}, "
            f"n_gpu_layers={self.n_gpu_layers})"
        )
