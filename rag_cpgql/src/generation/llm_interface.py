"""LLM interface using llama-cpp-python."""
from llama_cpp import Llama, LlamaGrammar
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMInterface:
    """Wrapper for llama-cpp-python LLM interface."""

    # Default model paths (proven best models from experiments)
    LLMXCPG_MODEL = r"C:\Users\user\.lmstudio\models\llmxcpg\LLMxCPG-Q\qwen2.5-coder-32B-instruct-bnb-q5_k_m.gguf"
    QWEN3_CODER_MODEL = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-Coder-30B-A3B-Instruct-GGUF\Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_llmxcpg: bool = True,
        n_ctx: int = 8192,
        n_gpu_layers: int = -1,
        n_batch: int = 512,
        n_threads: int = 8,
        verbose: bool = False
    ):
        """
        Initialize LLM.

        Args:
            model_path: Path to GGUF model file (None = use default)
            use_llmxcpg: Use LLMxCPG-Q model (100% CPGQL success rate)
            n_ctx: Context window size
            n_gpu_layers: GPU layers (-1 = all)
            n_batch: Batch size
            n_threads: CPU threads
            verbose: Enable verbose logging
        """
        # Select model: LLMxCPG-Q (best) or Qwen3-Coder (fallback)
        if model_path is None:
            if use_llmxcpg:
                model_path = self.LLMXCPG_MODEL
                logger.info("Using LLMxCPG-Q model (fine-tuned for CPGQL)")
            else:
                model_path = self.QWEN3_CODER_MODEL
                logger.info("Using Qwen3-Coder-32B model (general coder)")

        logger.info(f"Loading model: {model_path}")
        logger.info(f"Context size: {n_ctx}, GPU layers: {n_gpu_layers}")

        self.model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_batch=n_batch,
            n_threads=n_threads,
            verbose=verbose
        )

        logger.info("Model loaded successfully")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop: Optional[list] = None,
        grammar: Optional[LlamaGrammar] = None
    ) -> str:
        """
        Generate completion using chat format.

        Args:
            system_prompt: System instructions
            user_prompt: User input
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            stop: Stop sequences
            grammar: Optional LlamaGrammar for constrained generation

        Returns:
            Generated text
        """
        # Build chat prompt in ChatML format
        prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
"""

        if stop is None:
            stop = ["<|im_end|>", "<|endoftext|>"]

        logger.debug(f"Generating with temp={temperature}, max_tokens={max_tokens}, grammar={'enabled' if grammar else 'disabled'}")

        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop,
            echo=False,
            grammar=grammar
        )

        return response['choices'][0]['text'].strip()

    def generate_simple(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.6,
        grammar: Optional[LlamaGrammar] = None
    ) -> str:
        """
        Simple generation without chat formatting (for CPGQL queries).

        Args:
            prompt: Direct prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            grammar: Optional LlamaGrammar for constrained generation

        Returns:
            Generated text
        """
        logger.debug(f"Simple generation: temp={temperature}, max_tokens={max_tokens}, grammar={'enabled' if grammar else 'disabled'}")

        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False,
            grammar=grammar
        )

        return response['choices'][0]['text'].strip()

    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'model'):
            del self.model
