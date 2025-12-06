"""
RAGAS Configuration Module

Configuration and factory functions for RAGAS evaluation with different LLM providers.

Author: Configurable LLM Architecture - Week 2
Date: November 25, 2025
"""

import logging
from typing import Optional, Dict, List
from pathlib import Path
import yaml

from src.llm import BaseLLMProvider, create_llm_provider

logger = logging.getLogger(__name__)


class RAGASConfig:
    """
    Configuration for RAGAS evaluation.

    Attributes:
        use_separate_llm: Use separate LLM for RAGAS (different from generation LLM)
        provider_type: LLM provider type for RAGAS ("local", "gigachat", "openai")
        provider_config: Provider-specific configuration
        metrics: List of RAGAS metrics to compute
        batch_size: Batch size for evaluation
        max_samples: Maximum samples to evaluate (None = all)
    """

    def __init__(
        self,
        use_separate_llm: bool = False,
        provider_type: Optional[str] = None,
        provider_config: Optional[Dict] = None,
        metrics: Optional[List[str]] = None,
        batch_size: int = 10,
        max_samples: Optional[int] = None
    ):
        """
        Initialize RAGAS configuration.

        Args:
            use_separate_llm: Use separate LLM for RAGAS evaluation
            provider_type: LLM provider type (if None, uses main LLM config)
            provider_config: Provider-specific config dict
            metrics: List of metric names to compute
            batch_size: Batch size for evaluation
            max_samples: Max samples to evaluate (None = all)
        """
        self.use_separate_llm = use_separate_llm
        self.provider_type = provider_type
        self.provider_config = provider_config or {}
        self.metrics = metrics or [
            'context_precision',
            'context_recall',
            'answer_relevancy',
            'faithfulness'
        ]
        self.batch_size = batch_size
        self.max_samples = max_samples

    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> 'RAGASConfig':
        """
        Load RAGAS configuration from YAML file.

        Args:
            config_path: Path to config.yaml (if None, uses default)

        Returns:
            RAGASConfig instance
        """
        if config_path is None:
            config_path = Path(__file__).parents[2] / "config.yaml"

        logger.info(f"Loading RAGAS config from: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        ragas_config = config.get('ragas', {})

        return cls(
            use_separate_llm=ragas_config.get('use_separate_llm', False),
            provider_type=ragas_config.get('provider'),
            provider_config=ragas_config.get('provider_config', {}),
            metrics=ragas_config.get('metrics'),
            batch_size=ragas_config.get('batch_size', 10),
            max_samples=ragas_config.get('max_samples')
        )

    def create_llm_provider(self) -> BaseLLMProvider:
        """
        Create LLM provider for RAGAS based on configuration.

        Returns:
            BaseLLMProvider instance

        Example:
            config = RAGASConfig.from_yaml()
            provider = config.create_llm_provider()
        """
        if self.use_separate_llm and self.provider_type:
            # Create separate LLM for RAGAS
            logger.info(f"Creating separate RAGAS LLM: {self.provider_type}")

            config = {
                'llm': {
                    'provider': self.provider_type,
                    self.provider_type: self.provider_config
                }
            }

            return create_llm_provider(config)
        else:
            # Use main LLM config from config.yaml
            logger.info("Using main LLM configuration for RAGAS")
            return create_llm_provider()


def create_ragas_evaluator(
    llm_provider: Optional[BaseLLMProvider] = None,
    config_path: Optional[Path] = None
):
    """
    Factory function to create RAGASEvaluator with proper configuration.

    Args:
        llm_provider: Optional LLM provider. If None, creates from config.
        config_path: Optional path to config.yaml

    Returns:
        RAGASEvaluator instance

    Example:
        # Use default config
        evaluator = create_ragas_evaluator()

        # Use custom provider
        from src.llm import create_llm_provider, LLMConfig
        provider = create_llm_provider({'llm': {'provider': 'gigachat', ...}})
        evaluator = create_ragas_evaluator(provider)

        # Use specific config file
        evaluator = create_ragas_evaluator(config_path=Path('/path/to/config.yaml'))
    """
    from .ragas_evaluator import RAGASEvaluator

    if llm_provider is None:
        # Load config and create provider
        ragas_config = RAGASConfig.from_yaml(config_path)
        llm_provider = ragas_config.create_llm_provider()
        logger.info("Created RAGAS evaluator with config-based LLM provider")
    else:
        logger.info(f"Created RAGAS evaluator with provided LLM provider: {llm_provider.__class__.__name__}")

    return RAGASEvaluator(llm_provider=llm_provider)


# Convenience functions

def get_ragas_evaluator_with_local_llm() -> 'RAGASEvaluator':
    """
    Get RAGAS evaluator with local LLM.

    Returns:
        RAGASEvaluator configured with LocalLLMProvider
    """
    from src.llm import create_llm_provider
    from .ragas_evaluator import RAGASEvaluator

    provider = create_llm_provider({'llm': {'provider': 'local'}})
    return RAGASEvaluator(llm_provider=provider)


def get_ragas_evaluator_with_gigachat(
    credentials: Optional[str] = None,
    model: str = "GigaChat-Pro"
) -> 'RAGASEvaluator':
    """
    Get RAGAS evaluator with GigaChat API.

    Args:
        credentials: GigaChat credentials (if None, uses env variable)
        model: GigaChat model name

    Returns:
        RAGASEvaluator configured with GigaChatProvider
    """
    from src.llm import create_llm_provider
    from .ragas_evaluator import RAGASEvaluator
    import os

    if credentials is None:
        credentials = os.getenv('GIGACHAT_CREDENTIALS')

    if not credentials:
        raise ValueError(
            "GigaChat credentials not provided. "
            "Set GIGACHAT_CREDENTIALS environment variable or pass credentials parameter."
        )

    config = {
        'llm': {
            'provider': 'gigachat',
            'gigachat': {
                'credentials': credentials,
                'model': model,
                'scope': 'GIGACHAT_API_PERS'
            }
        }
    }

    provider = create_llm_provider(config)
    return RAGASEvaluator(llm_provider=provider)


# Example configurations

RAGAS_CONFIGS = {
    'local_fast': {
        'use_separate_llm': False,
        'metrics': ['context_precision', 'answer_relevancy'],
        'batch_size': 20
    },
    'local_full': {
        'use_separate_llm': False,
        'metrics': ['context_precision', 'context_recall', 'answer_relevancy', 'faithfulness'],
        'batch_size': 10
    },
    'gigachat_fast': {
        'use_separate_llm': True,
        'provider_type': 'gigachat',
        'provider_config': {
            'model': 'GigaChat-Pro',
            'temperature': 0.5
        },
        'metrics': ['context_precision', 'answer_relevancy'],
        'batch_size': 20
    },
    'gigachat_full': {
        'use_separate_llm': True,
        'provider_type': 'gigachat',
        'provider_config': {
            'model': 'GigaChat-Max',
            'temperature': 0.3
        },
        'metrics': ['context_precision', 'context_recall', 'answer_relevancy', 'faithfulness'],
        'batch_size': 5
    }
}


def get_preset_config(preset_name: str) -> RAGASConfig:
    """
    Get predefined RAGAS configuration.

    Args:
        preset_name: Name of preset ('local_fast', 'local_full', 'gigachat_fast', 'gigachat_full')

    Returns:
        RAGASConfig instance

    Example:
        config = get_preset_config('gigachat_fast')
        provider = config.create_llm_provider()
        evaluator = RAGASEvaluator(llm_provider=provider)
    """
    if preset_name not in RAGAS_CONFIGS:
        raise ValueError(
            f"Unknown preset: {preset_name}. "
            f"Available presets: {', '.join(RAGAS_CONFIGS.keys())}"
        )

    preset = RAGAS_CONFIGS[preset_name]
    return RAGASConfig(**preset)
