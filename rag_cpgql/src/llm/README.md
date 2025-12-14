# LLM Module

Pluggable LLM provider system supporting multiple backends including local llama.cpp, GigaChat, and OpenAI-compatible APIs.

## Overview

```
src/llm/
├── factory.py           # Provider factory (main entry point)
├── base_provider.py     # Abstract base class
├── local_provider.py    # llama-cpp-python provider
├── gigachat_provider.py # GigaChat API provider
├── openai_provider.py   # OpenAI/Azure provider
├── llm_interface_compat.py # Compatibility layer
└── langchain_adapter.py # LangChain integration
```

## Usage

### Factory Pattern

```python
from src.llm.factory import create_llm_provider, get_global_provider

# Create provider from config
provider = create_llm_provider()

# Generate response
response = provider.generate(
    prompt="What is MVCC in PostgreSQL?",
    temperature=0.7,
    max_tokens=512
)

# Singleton pattern
provider = get_global_provider()  # Returns same instance
```

### Direct Provider Usage

```python
from src.llm.gigachat_provider import GigaChatProvider

provider = GigaChatProvider(
    credentials="your-credentials",
    model="GigaChat-Pro"
)

response = provider.generate("Explain buffer management")
```

## Supported Providers

| Provider | Model | Requirements |
|----------|-------|--------------|
| `local` | Qwen3-Coder-30B, etc. | llama-cpp-python, model file |
| `gigachat` | GigaChat-Pro | langchain-gigachat, API key |
| `openai` | gpt-4o, gpt-4 | openai library, API key |

## Configuration

```yaml
llm:
  provider: gigachat  # local, gigachat, openai

  gigachat:
    credentials: ${GIGACHAT_CREDENTIALS}
    model: GigaChat-Pro
    temperature: 0.1
    scope: GIGACHAT_API_PERS

  local:
    model_path: /models/qwen3-coder-30b.gguf
    n_ctx: 8192
    n_gpu_layers: -1
    temperature: 0.1

  openai:
    api_key: ${OPENAI_API_KEY}
    model: gpt-4o
    temperature: 0.1
```

## Provider Interface

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """Generate text response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        pass
```

## Local Provider (llama.cpp)

```python
from src.llm.local_provider import LocalLLMProvider

provider = LocalLLMProvider(
    model_path="/models/qwen3-coder-30b.gguf",
    n_ctx=8192,
    n_gpu_layers=-1,  # Use all GPU layers
)

# Generate with grammar constraint
response = provider.generate(
    prompt="Generate CPGQL query",
    grammar_file="cpgql.gbnf"
)
```

## GigaChat Provider

```python
from src.llm.gigachat_provider import GigaChatProvider

provider = GigaChatProvider(
    credentials=os.environ["GIGACHAT_CREDENTIALS"],
    model="GigaChat-Pro",
    scope="GIGACHAT_API_PERS"
)

# Streaming response
for chunk in provider.stream("Explain MVCC"):
    print(chunk, end="")
```

## LangChain Integration

```python
from src.llm.langchain_adapter import get_langchain_llm

# Get LangChain-compatible LLM
llm = get_langchain_llm()

# Use with LangChain
from langchain.chains import LLMChain
chain = LLMChain(llm=llm, prompt=template)
```

## Security Integration

Providers can be wrapped with security layer:

```python
from src.llm.factory import create_llm_provider

# If security.enabled = true in config
provider = create_llm_provider()
# Returns SecureLLMProvider with DLP filtering
```

## Error Handling

```python
from src.llm.factory import create_llm_provider, LLMError

try:
    provider = create_llm_provider()
    response = provider.generate("test")
except LLMError as e:
    print(f"LLM error: {e}")
```

## See Also

- `/docs/integrations/GIGACHAT.md` - GigaChat setup
- `/src/generation/` - Query generation with LLM
- `/src/security/` - DLP integration
