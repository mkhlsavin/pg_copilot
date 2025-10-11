# LLM Interface Module Documentation

## Overview

The `llm_interface.py` module provides a Python interface to llama.cpp for local inference with the Qwen3-32B model, optimized for RTX 3090 (24GB VRAM) with CUDA 12.4 support.

## Purpose

- Load and initialize Qwen3-32B-Q4_K_M model
- Manage GPU memory efficiently
- Provide batched inference capabilities
- Handle generation parameters and errors
- Support streaming output (optional)

## Architecture

```
┌──────────────────────────────────────────────────┐
│            LLM Interface Module                   │
├──────────────────────────────────────────────────┤
│                                                   │
│  Model:                                           │
│    - Qwen3-32B-Q4_K_M.gguf                        │
│    - llama-cpp-python bindings                    │
│    - CUDA 12.4 acceleration                       │
│                                                   │
│  Capabilities:                                    │
│    1. Model loading and initialization            │
│    2. GPU memory management (24GB RTX 3090)       │
│    3. Prompt formatting for Qwen3                 │
│    4. Text generation with parameters             │
│    5. Batch processing                            │
│    6. Error handling and retry logic              │
│                                                   │
│  Output:                                          │
│    - Generated text responses                     │
│                                                   │
└──────────────────────────────────────────────────┘
```

## Key Components

### 1. LLMInterface Class

Main class for LLM inference.

```python
class LLMInterface:
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 8192,
        n_gpu_layers: int = -1,
        n_batch: int = 512,
        verbose: bool = False
    ):
        """
        Initialize LLM interface.

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size (max tokens)
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

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: List[str] = None
    ) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling threshold
            stop: Stop sequences

        Returns:
            Generated text
        """

    def generate_batch(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[str]:
        """Generate for multiple prompts."""

    def unload_model(self):
        """Free GPU memory."""
```

### 2. Core Functions

#### `load_model() -> Llama`

Loads GGUF model using llama-cpp-python.

**Implementation:**
```python
from llama_cpp import Llama

def load_model(
    model_path: str,
    n_ctx: int = 8192,
    n_gpu_layers: int = -1,
    n_batch: int = 512,
    verbose: bool = False
) -> Llama:
    """
    Load Qwen3-32B model with CUDA support.

    GPU Configuration for RTX 3090 (24GB):
        - n_gpu_layers=-1: Offload all layers to GPU
        - n_ctx=8192: 8K context window (fits in 24GB)
        - n_batch=512: Batch size for prompt processing
    """
    llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        n_batch=n_batch,
        verbose=verbose,
        # CUDA-specific settings
        n_threads=8,  # CPU threads for non-GPU operations
        use_mmap=True,  # Memory-map model file
        use_mlock=False,  # Don't lock memory (allows swap if needed)
        # Generation defaults
        logits_all=False,  # Save memory
        embedding=False,
    )

    return llm
```

**Memory Estimates (Qwen3-32B Q4_K_M):**
- Model size: ~18-20 GB
- Context buffer (8192 tokens): ~2-3 GB
- Generation overhead: ~1-2 GB
- **Total:** ~22-24 GB (fits RTX 3090)

#### `format_qwen3_prompt(prompt: str, system_prompt: str = None) -> str`

Formats prompt for Qwen3 chat template.

**Qwen3 Format:**
```
<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
```

**Implementation:**
```python
def format_qwen3_prompt(prompt: str, system_prompt: str = None) -> str:
    """
    Format prompt using Qwen3 chat template.

    Args:
        prompt: User input
        system_prompt: Optional system instructions

    Returns:
        Formatted prompt
    """
    if system_prompt is None:
        system_prompt = "You are a helpful assistant specialized in PostgreSQL internals."

    formatted = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""

    return formatted
```

#### `generate(llm: Llama, prompt: str, **kwargs) -> str`

Generates text from prompt.

**Implementation:**
```python
def generate(
    llm: Llama,
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 40,
    repeat_penalty: float = 1.1,
    stop: List[str] = None
) -> str:
    """
    Generate text with llama.cpp.

    Generation Parameters:
        - temperature: Controls randomness (0.0 = deterministic, 1.0 = balanced, 2.0 = very random)
        - top_p: Nucleus sampling (0.9 = consider top 90% probability mass)
        - top_k: Consider top K tokens (40 is good default)
        - repeat_penalty: Penalize repetition (1.0 = none, 1.1 = slight penalty)
        - stop: Stop generation at these sequences
    """
    if stop is None:
        stop = ["<|im_end|>", "<|endoftext|>"]

    # Generate
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        stop=stop,
        echo=False  # Don't include prompt in output
    )

    # Extract generated text
    generated_text = output['choices'][0]['text']

    return generated_text.strip()
```

#### `generate_batch(llm: Llama, prompts: List[str], **kwargs) -> List[str]`

Batch generation with progress tracking.

**Implementation:**
```python
from tqdm import tqdm

def generate_batch(
    llm: Llama,
    prompts: List[str],
    show_progress: bool = True,
    **kwargs
) -> List[str]:
    """
    Generate responses for multiple prompts.

    Note: llama-cpp-python processes sequentially,
    but this provides progress tracking and error handling.
    """
    results = []

    iterator = tqdm(prompts, desc="Generating") if show_progress else prompts

    for prompt in iterator:
        try:
            response = generate(llm, prompt, **kwargs)
            results.append(response)
        except Exception as e:
            print(f"Error generating response: {e}")
            results.append("")  # Empty response on error

    return results
```

#### `estimate_tokens(text: str) -> int`

Estimates token count (approximate).

**Implementation:**
```python
def estimate_tokens(text: str) -> int:
    """
    Rough token estimate (1 token ≈ 4 characters for English).

    For accurate counting, use llm.tokenize()
    """
    return len(text) // 4

def count_tokens_exact(llm: Llama, text: str) -> int:
    """
    Exact token count using model tokenizer.
    """
    tokens = llm.tokenize(text.encode('utf-8'))
    return len(tokens)
```

## Configuration

Key settings in `config.py`:

```python
# LLM configuration
MODEL_PATH = r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf"
LLAMA_CPP_PATH = r"C:\Users\user\llama.cpp"

# Model parameters
N_CTX = 8192  # Context window
N_GPU_LAYERS = -1  # All layers on GPU
N_BATCH = 512  # Batch size for processing
N_THREADS = 8  # CPU threads

# Generation parameters
TEMPERATURE = 0.7  # Sampling temperature
TOP_P = 0.9  # Nucleus sampling
TOP_K = 40  # Top-k sampling
REPEAT_PENALTY = 1.1  # Repetition penalty
MAX_TOKENS = 2048  # Max tokens per generation
STOP_SEQUENCES = ["<|im_end|>", "<|endoftext|>"]

# System prompt
SYSTEM_PROMPT = """You are a PostgreSQL internals expert with deep knowledge of the PostgreSQL 17 architecture and source code. Generate high-quality question-answer pairs based on developer discussions and source code context."""
```

## Memory Management

### RTX 3090 Optimization (24GB VRAM)

**Full GPU Offload:**
```python
# Offload all layers to GPU
llm = Llama(
    model_path=MODEL_PATH,
    n_gpu_layers=-1,  # All layers
    n_ctx=8192,       # 8K context
    n_batch=512       # Batch size
)
```

**Memory-Constrained Setup (if needed):**
```python
# Partial GPU offload + smaller context
llm = Llama(
    model_path=MODEL_PATH,
    n_gpu_layers=40,  # Partial offload (adjust as needed)
    n_ctx=4096,       # Smaller context
    n_batch=256       # Smaller batch
)
```

**Check GPU Memory Usage:**
```python
import torch

def check_gpu_memory():
    """Check CUDA memory usage."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3

        print(f"GPU Memory:")
        print(f"  Allocated: {allocated:.2f} GB")
        print(f"  Reserved: {reserved:.2f} GB")
        print(f"  Total: {total:.2f} GB")
        print(f"  Free: {total - reserved:.2f} GB")
```

## Usage Examples

### Basic Usage

```python
from llm_interface import LLMInterface

# Initialize
llm_interface = LLMInterface(
    model_path=r"C:\Users\user\.lmstudio\models\lmstudio-community\Qwen3-32B-GGUF\Qwen3-32B-Q4_K_M.gguf",
    n_ctx=8192,
    n_gpu_layers=-1,
    n_batch=512
)

# Load model
print("Loading model...")
llm_interface.load_model()

# Generate response
prompt = "Explain PostgreSQL's MVCC implementation."
response = llm_interface.generate(
    prompt=prompt,
    max_tokens=1024,
    temperature=0.7
)

print(response)

# Unload model when done
llm_interface.unload_model()
```

### Batch Generation

```python
from llm_interface import LLMInterface

llm_interface = LLMInterface(...)
llm_interface.load_model()

# Multiple prompts
prompts = [
    "Explain PostgreSQL's buffer manager.",
    "How does PostgreSQL implement B-tree indexes?",
    "Describe the query planner's cost estimation."
]

# Generate batch
responses = llm_interface.generate_batch(
    prompts=prompts,
    max_tokens=512,
    temperature=0.7,
    show_progress=True
)

for prompt, response in zip(prompts, responses):
    print(f"Q: {prompt}")
    print(f"A: {response}\n")
```

### Streaming Generation (Advanced)

```python
from llm_interface import LLMInterface

llm_interface = LLMInterface(...)
llm_interface.load_model()

# Stream tokens as they're generated
prompt = llm_interface.format_qwen3_prompt("Explain WAL in PostgreSQL.")

for token in llm_interface.llm(
    prompt,
    max_tokens=512,
    temperature=0.7,
    stream=True
):
    print(token['choices'][0]['text'], end='', flush=True)

print()
```

### Error Handling and Retry

```python
import time

def generate_with_retry(llm_interface, prompt, max_retries=3, **kwargs):
    """
    Generate with retry logic for robustness.
    """
    for attempt in range(max_retries):
        try:
            response = llm_interface.generate(prompt, **kwargs)
            return response
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

    return None
```

## Performance Considerations

### Estimated Metrics

- **Model loading:** 30-60 seconds
- **Generation speed:** ~20-40 tokens/second (RTX 3090)
- **8K context:** ~10-15 tokens/second
- **Per-QA generation:** ~1-2 minutes (for 3-5 QA pairs)

### Optimization Strategies

1. **Keep Model Loaded**
   ```python
   # Load once, generate many times
   llm_interface.load_model()
   for prompt in prompts:
       response = llm_interface.generate(prompt)
   llm_interface.unload_model()
   ```

2. **Adjust Context Size**
   ```python
   # Use only what you need
   # Shorter context = faster + less memory
   n_ctx = len(prompt_tokens) + max_tokens + 512  # Buffer
   ```

3. **Parallel Generation (Multiple GPUs)**
   ```python
   # If you have multiple GPUs
   import torch.multiprocessing as mp

   def worker(gpu_id, prompts, results):
       torch.cuda.set_device(gpu_id)
       llm = LLMInterface(...)
       llm.load_model()
       for prompt in prompts:
           results.append(llm.generate(prompt))

   # Split prompts across GPUs
   # (Not applicable for single RTX 3090, but useful for scaling)
   ```

## Dependencies

```
llama-cpp-python>=0.2.0
torch>=2.0.0  # For CUDA support
tqdm>=4.66.0
```

## Installation

### Install llama-cpp-python with CUDA 12.4

```bash
# Activate conda environment
conda activate llama.cpp

# Install with CUDA support
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# Verify installation
python -c "from llama_cpp import Llama; print('llama-cpp-python installed successfully')"
```

## Testing

### Unit Tests

```python
import unittest
from llm_interface import LLMInterface, format_qwen3_prompt

class TestLLMInterface(unittest.TestCase):
    def test_prompt_formatting(self):
        prompt = "Test question"
        formatted = format_qwen3_prompt(prompt)
        self.assertIn("<|im_start|>system", formatted)
        self.assertIn("<|im_start|>user", formatted)
        self.assertIn("Test question", formatted)

    def test_token_estimation(self):
        text = "This is a test."
        tokens = estimate_tokens(text)
        self.assertGreater(tokens, 0)
```

### Integration Tests

```python
# Test model loading and generation
llm_interface = LLMInterface(
    model_path=MODEL_PATH,
    n_ctx=512,  # Small context for testing
    n_gpu_layers=-1
)

llm_interface.load_model()
response = llm_interface.generate("Say hello.", max_tokens=50)
assert len(response) > 0
llm_interface.unload_model()
```

## Troubleshooting

### GPU Out of Memory

**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**
```python
# Reduce context window
N_CTX = 4096  # Instead of 8192

# Reduce batch size
N_BATCH = 256  # Instead of 512

# Partial GPU offload
N_GPU_LAYERS = 40  # Instead of -1
```

### Slow Generation

**Symptoms:** <5 tokens/second

**Solutions:**
- Verify GPU is being used: `nvidia-smi`
- Check `n_gpu_layers=-1` (full offload)
- Reduce `n_ctx` if too large
- Close other GPU applications

### Model Loading Fails

**Symptoms:**
```
Failed to load model from ...
```

**Solutions:**
- Verify model path exists
- Check file permissions
- Ensure enough system RAM (>32GB recommended)
- Verify GGUF format is correct

### llama-cpp-python Import Error

**Symptoms:**
```
ImportError: cannot import name 'Llama'
```

**Solutions:**
```bash
# Reinstall with CUDA support
pip uninstall llama-cpp-python
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

## Next Steps

After LLM interface is working:
1. Test generation with sample prompts
2. Verify GPU utilization and speed
3. Proceed to `qa_generator.py` for QA pair generation
