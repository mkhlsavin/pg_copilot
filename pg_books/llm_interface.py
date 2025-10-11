"""
LLM Interface Module

Provides interface to llama.cpp for local inference with Qwen3-32B.
"""
import logging
from typing import List, Optional

from llama_cpp import Llama

import config


logger = logging.getLogger(__name__)


class LLMInterface:
    """Interface to llama.cpp for text generation."""

    def __init__(
        self,
        model_path: str = config.MODEL_PATH,
        n_ctx: int = config.N_CTX,
        n_gpu_layers: int = config.N_GPU_LAYERS,
        n_batch: int = config.N_BATCH,
        verbose: bool = False
    ):
        """
        Initialize LLM interface.

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_gpu_layers: GPU layers to offload (-1 = all)
            n_batch: Batch size for processing
            verbose: Enable verbose logging
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_batch = n_batch
        self.verbose = verbose
        self.llm = None

    def load_model(self):
        """Load model into memory."""
        logger.info(f"Loading model: {self.model_path}")
        logger.info(f"  Context size: {self.n_ctx}")
        logger.info(f"  GPU layers: {self.n_gpu_layers}")
        logger.info(f"  Batch size: {self.n_batch}")

        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            n_batch=self.n_batch,
            n_threads=config.N_THREADS,
            verbose=self.verbose,
            use_mmap=True,
            use_mlock=False,
            logits_all=False,
            embedding=False
        )

        logger.info("Model loaded successfully")

    def format_qwen3_prompt(self, prompt: str, system_prompt: str = None) -> str:
        """
        Format prompt using Qwen3 chat template.

        Args:
            prompt: User input
            system_prompt: Optional system instructions

        Returns:
            Formatted prompt
        """
        if system_prompt is None:
            system_prompt = config.SYSTEM_PROMPT

        formatted = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
        return formatted

    def generate(
        self,
        prompt: str,
        max_tokens: int = config.MAX_TOKENS,
        temperature: float = config.TEMPERATURE,
        top_p: float = config.TOP_P,
        top_k: int = config.TOP_K,
        repeat_penalty: float = config.REPEAT_PENALTY,
        stop: List[str] = None,
        format_prompt: bool = True
    ) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            repeat_penalty: Repetition penalty
            stop: Stop sequences
            format_prompt: Apply Qwen3 chat template

        Returns:
            Generated text
        """
        if self.llm is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Format prompt if requested
        if format_prompt:
            prompt = self.format_qwen3_prompt(prompt)

        # Default stop sequences
        if stop is None:
            stop = config.STOP_SEQUENCES

        logger.debug(f"Generating with max_tokens={max_tokens}, temp={temperature}")

        # Generate
        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            stop=stop,
            echo=False
        )

        # Extract generated text
        generated_text = output['choices'][0]['text']

        return generated_text.strip()

    def generate_batch(
        self,
        prompts: List[str],
        show_progress: bool = True,
        **kwargs
    ) -> List[str]:
        """
        Generate responses for multiple prompts.

        Args:
            prompts: List of prompts
            show_progress: Show progress bar
            **kwargs: Generation parameters

        Returns:
            List of generated texts
        """
        from tqdm import tqdm

        results = []
        iterator = tqdm(prompts, desc="Generating") if show_progress else prompts

        for prompt in iterator:
            try:
                response = self.generate(prompt, **kwargs)
                results.append(response)
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                results.append("")  # Empty response on error

        return results

    def unload_model(self):
        """Free GPU memory."""
        if self.llm is not None:
            del self.llm
            self.llm = None
            logger.info("Model unloaded")


def main():
    """Main function for testing."""
    from utils import setup_logging

    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    logger.info("Testing LLM interface")

    # Initialize
    llm_interface = LLMInterface()

    # Load model
    llm_interface.load_model()

    # Test generation
    test_prompt = "Explain PostgreSQL's MVCC implementation in 2-3 sentences."

    logger.info(f"Test prompt: {test_prompt}")

    response = llm_interface.generate(
        test_prompt,
        max_tokens=512,
        temperature=0.7
    )

    logger.info(f"Response: {response}")

    # Unload
    llm_interface.unload_model()

    logger.info("LLM interface test complete")


if __name__ == '__main__':
    main()
