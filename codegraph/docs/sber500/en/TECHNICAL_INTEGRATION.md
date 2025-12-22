# CodeGraph: GigaChat Technical Integration

## Table of Contents

- [Overview](#overview)
- [1. INTEGRATION ARCHITECTURE](#1-integration-architecture)
  - [1.1 LLM Provider Layer](#11-llm-provider-layer)
  - [1.2 Key Files](#12-key-files)
- [2. GIGACHAT PROVIDER](#2-gigachat-provider)
  - [2.1 Initialization](#21-initialization)
  - [2.2 Main Methods](#22-main-methods)
- [3. CONFIGURATION](#3-configuration)
  - [3.1 config.yaml](#31-configyaml)
  - [3.2 Environment Variables](#32-environment-variables)
  - [3.3 Supported Models](#33-supported-models)
- [4. ERROR HANDLING](#4-error-handling)
  - [4.1 Rate Limiting](#41-rate-limiting)
  - [4.2 Exception Types](#42-exception-types)
- [5. USAGE IN AGENTS](#5-usage-in-agents)
  - [5.1 Analyzer Agent](#51-analyzer-agent)
  - [5.2 Generator Agent](#52-generator-agent)
  - [5.3 Interpreter Agent](#53-interpreter-agent)
- [6. FACTORY PATTERN](#6-factory-pattern)
  - [6.1 Provider Creation](#61-provider-creation)
  - [6.2 Usage](#62-usage)
- [7. LANGCHAIN ADAPTER](#7-langchain-adapter)
  - [7.1 RAGAS Integration](#71-ragas-integration)
  - [7.2 Usage with RAGAS](#72-usage-with-ragas)
- [8. TESTING](#8-testing)
  - [8.1 Setup Verification](#81-setup-verification)
  - [8.2 Unit Tests](#82-unit-tests)
- [9. MONITORING](#9-monitoring)
  - [9.1 Metrics](#91-metrics)
  - [9.2 Logging](#92-logging)
- [10. SECURITY](#10-security)
  - [10.1 Credentials Storage](#101-credentials-storage)
  - [10.2 Input Validation](#102-input-validation)
- [11. DEPENDENCIES](#11-dependencies)
  - [requirements.txt](#requirementstxt)
- [12. FAQ](#12-faq)
  - [Q: How to get GIGACHAT_AUTH_KEY?](#q-how-to-get-gigachat_auth_key)
  - [Q: Which model to choose?](#q-which-model-to-choose)
  - [Q: How to optimize prompts?](#q-how-to-optimize-prompts)
  - [Q: What to do with rate limiting?](#q-what-to-do-with-rate-limiting)

## Overview

This document describes the technical architecture of GigaChat integration in the CodeGraph system - an AI copilot for source code analysis.

---

## 1. INTEGRATION ARCHITECTURE

### 1.1 LLM Provider Layer

```
+-----------------------------------------------------------+
|              LLM Provider Interface                        |
|           src/llm/base_provider.py                         |
+---------------------------+-------------------------------+
                            |
          +-----------------+-----------------+
          |                 |                 |
     +----v----+       +----v----+       +----v----+
     |  Local  |       | GigaChat|       | OpenAI  |
     | (llama) |       | Provider|       | Provider|
     +---------+       +---------+       +---------+
                            |
                            v
              +-----------------+
              | LangChain       |
              | Adapter         |
              | (for RAGAS)     |
              +-----------------+
```

### 1.2 Key Files

| File | Purpose | Lines of Code |
|------|---------|---------------|
| `src/llm/gigachat_provider.py` | Main GigaChat provider | 431 |
| `src/llm/factory.py` | Provider factory | 150 |
| `src/llm/base_provider.py` | Base interface | 120 |
| `src/llm/langchain_adapter.py` | RAGAS adapter | 80 |
| `src/evaluation/ragas_config.py` | RAGAS configuration | 200 |

---

## 2. GIGACHAT PROVIDER

### 2.1 Initialization

```python
from src.llm.gigachat_provider import GigaChatProvider
from src.llm.base_provider import LLMConfig
import os

# Configuration
config = LLMConfig(
    provider_type='gigachat',
    temperature=0.7,
    max_tokens=2000,
    extra_params={
        'credentials': os.getenv('GIGACHAT_AUTH_KEY'),
        'model': 'GigaChat-2-Pro',
        'scope': 'GIGACHAT_API_PERS',
        'verify_ssl_certs': True,
        'timeout': 60,
    }
)

# Create provider
provider = GigaChatProvider(config)
```

### 2.2 Main Methods

#### generate() - Main Generation Method

```python
def generate(
    self,
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> LLMResponse:
    """
    Generate response with separated system/user prompts.

    Args:
        system_prompt: System prompt (role, instructions)
        user_prompt: User request
        **kwargs: Additional parameters (temperature, max_tokens)

    Returns:
        LLMResponse with fields:
            - content: str - generated text
            - metadata: dict - call information
    """
```

**Usage Example:**

```python
response = provider.generate(
    system_prompt="""You are an expert in PostgreSQL code analysis.
    Analyze questions and determine intent.""",
    user_prompt="Find SQL injection vulnerabilities"
)

print(response.content)
# "Intent: security-check
#  Keywords: SQL, injection
#  Scenario: vulnerability_detection"

print(response.metadata)
# {
#   'model': 'GigaChat-2-Pro',
#   'provider': 'gigachat',
#   'scope': 'GIGACHAT_API_PERS',
#   'usage': {'total_tokens': 150, 'prompt_tokens': 80, 'completion_tokens': 70}
# }
```

#### generate_simple() - Simple Generation

```python
def generate_simple(self, prompt: str, **kwargs) -> LLMResponse:
    """
    Simple generation without system/user separation.
    Sends prompt as HumanMessage.
    """
```

#### generate_stream() - Streaming Generation

```python
def generate_stream(
    self,
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> Generator[str, None, None]:
    """
    Streaming generation for long responses.
    Uses client.stream() for chunks.

    Yields:
        str: Text chunks as received
    """
```

**Example:**

```python
for chunk in provider.generate_stream(
    system_prompt="You are a PostgreSQL expert",
    user_prompt="Explain MVCC mechanism in detail"
):
    print(chunk, end='', flush=True)
```

---

## 3. CONFIGURATION

### 3.1 config.yaml

```yaml
llm:
  # Provider selection: "gigachat", "local", "openai"
  provider: "gigachat"

  gigachat:
    # Client identifier (optional)
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"

    # Authorization key (from environment variable)
    credentials: ${GIGACHAT_AUTH_KEY}

    # Model
    # Options: "GigaChat-2", "GigaChat-2-Pro", "GigaChat-2-Max"
    model: "GigaChat-2-Pro"

    # Custom endpoint (optional)
    base_url: null

    # SSL verification
    # false for development, true for production
    verify_ssl_certs: true

    # Access scope
    # Options: GIGACHAT_API_PERS, GIGACHAT_API_CORP, GIGACHAT_API_B2B
    scope: "GIGACHAT_API_PERS"

    # Request timeout (seconds)
    timeout: 60

    # Generation parameters
    temperature: 0.7
    max_tokens: 2000
    top_p: null  # Use GigaChat default
```

### 3.2 Environment Variables

```bash
# Required
export GIGACHAT_AUTH_KEY="your_base64_encoded_key"

# Optional
export GIGACHAT_CLIENT_ID="019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
export GIGACHAT_SCOPE="GIGACHAT_API_PERS"
export GIGACHAT_MODEL="GigaChat-2-Pro"
```

### 3.3 Supported Models

| Model | Description | Recommendation |
|-------|-------------|----------------|
| GigaChat-2 | Base v2 model | Development, fast queries |
| GigaChat-2-Pro | Advanced v2 | **Production (primary)** |
| GigaChat-2-Max | Maximum quality | Critical tasks |
| GigaChat | Legacy base | Compatibility |
| GigaChat-Pro | Legacy advanced | Compatibility |
| GigaChat-Plus | Legacy extended | Compatibility |

---

## 4. ERROR HANDLING

### 4.1 Rate Limiting

```python
# Retry logic constants
MAX_RETRIES = 5
BASE_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 60.0  # seconds

def _is_rate_limit_error(error: Exception) -> bool:
    """Determine if error is rate limit."""
    error_msg = str(error).lower()
    return any(phrase in error_msg for phrase in [
        '429', 'rate limit', 'too many requests'
    ])

def _retry_with_backoff(func, *args, **kwargs):
    """
    Exponential backoff with jitter.

    Delay = min(BASE_RETRY_DELAY * 2^attempt + jitter, MAX_RETRY_DELAY)
    """
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not _is_rate_limit_error(e):
                raise
            if attempt == MAX_RETRIES - 1:
                raise

            delay = min(
                BASE_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1),
                MAX_RETRY_DELAY
            )
            time.sleep(delay)
```

### 4.2 Exception Types

```python
class GigaChatProviderError(Exception):
    """Base provider exception."""
    pass

class GigaChatAuthError(GigaChatProviderError):
    """Authorization error."""
    pass

class GigaChatRateLimitError(GigaChatProviderError):
    """Rate limit exceeded."""
    pass

class GigaChatAPIError(GigaChatProviderError):
    """General API error."""
    pass
```

---

## 5. USAGE IN AGENTS

### 5.1 Analyzer Agent

```python
# src/agents/analyzer_agent.py

class AnalyzerAgent:
    """Agent for user query intent analysis."""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def analyze(self, question: str) -> AnalysisResult:
        system_prompt = """You are an expert in codebase query analysis.
        Determine:
        1. Intent: find-function, explain-concept, security-check, etc.
        2. Keywords: key terms for search
        3. Domain: vacuum, wal, mvcc, query-planning, memory, etc.
        4. Confidence: classification confidence (0-1)
        """

        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=question
        )

        return self._parse_response(response.content)
```

### 5.2 Generator Agent

```python
# src/agents/generator_agent.py

class GeneratorAgent:
    """Agent for SQL query generation against CPG database."""

    def generate_query(self, context: str, question: str) -> str:
        system_prompt = """You are a CPG (Code Property Graph) SQL query expert.
        Based on context, generate a SQL query for DuckDB CPG database.

        Available tables:
        - nodes_method: id, name, signature, filename, line_number
        - edges_call: src, dst, call_line
        - tags: entity_id, tag_name, tag_value

        Response format: only SQL query without explanations.
        """

        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=f"Context:\n{context}\n\nQuestion: {question}"
        )

        return self._clean_query(response.content)
```

### 5.3 Interpreter Agent

```python
# src/agents/interpreter_agent.py

class InterpreterAgent:
    """Agent for result interpretation."""

    def interpret(self, question: str, results: list) -> str:
        system_prompt = """You are an expert in explaining code analysis results.
        Synthesize query results into an understandable response.

        Rules:
        1. Group by categories (Critical/High/Medium/Low for vulnerabilities)
        2. Specify exact file paths and line numbers
        3. Provide fix recommendations
        4. Use bullet lists for structure
        """

        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=f"Question: {question}\n\nResults:\n{json.dumps(results, ensure_ascii=False)}"
        )

        return response.content
```

---

## 6. FACTORY PATTERN

### 6.1 Provider Creation

```python
# src/llm/factory.py

def create_llm_provider(config: dict = None) -> BaseLLMProvider:
    """
    Factory method for LLM provider creation.

    Args:
        config: Configuration (if None, loads from config.yaml)

    Returns:
        Provider instance (GigaChatProvider, LocalProvider, etc.)
    """
    if config is None:
        config = load_config()

    provider_type = config.get('llm', {}).get('provider', 'gigachat')

    if provider_type == 'gigachat':
        return _create_gigachat_provider(config)
    elif provider_type == 'local':
        return _create_local_provider(config)
    elif provider_type == 'openai':
        return _create_openai_provider(config)
    else:
        raise ValueError(f"Unknown provider: {provider_type}")

def _create_gigachat_provider(config: dict) -> GigaChatProvider:
    """Create GigaChat provider from configuration."""
    gigachat_config = config.get('llm', {}).get('gigachat', {})

    return GigaChatProvider(LLMConfig(
        provider_type='gigachat',
        temperature=gigachat_config.get('temperature', 0.7),
        max_tokens=gigachat_config.get('max_tokens', 2000),
        extra_params={
            'credentials': gigachat_config.get('credentials'),
            'model': gigachat_config.get('model', 'GigaChat-2-Pro'),
            'scope': gigachat_config.get('scope', 'GIGACHAT_API_PERS'),
            'verify_ssl_certs': gigachat_config.get('verify_ssl_certs', True),
            'timeout': gigachat_config.get('timeout', 60),
        }
    ))
```

### 6.2 Usage

```python
from src.llm import create_llm_provider

# Auto-load from config.yaml
provider = create_llm_provider()

# Or with custom configuration
custom_config = {
    'llm': {
        'provider': 'gigachat',
        'gigachat': {
            'credentials': 'my_key',
            'model': 'GigaChat-2-Max'
        }
    }
}
provider = create_llm_provider(custom_config)
```

---

## 7. LANGCHAIN ADAPTER

### 7.1 RAGAS Integration

```python
# src/llm/langchain_adapter.py

from langchain_core.language_models import BaseLLM

class LangChainGigaChatAdapter(BaseLLM):
    """Adapter for LangChain/RAGAS compatibility."""

    provider: GigaChatProvider

    def _call(self, prompt: str, **kwargs) -> str:
        response = self.provider.generate_simple(prompt, **kwargs)
        return response.content

    @property
    def _llm_type(self) -> str:
        return "gigachat"

def create_langchain_adapter(provider: BaseLLMProvider) -> BaseLLM:
    """Create LangChain-compatible adapter."""
    return LangChainGigaChatAdapter(provider=provider)
```

### 7.2 Usage with RAGAS

```python
from ragas import evaluate
from src.llm import create_llm_provider, create_langchain_adapter

# Create provider and adapter
provider = create_llm_provider()
langchain_llm = create_langchain_adapter(provider)

# RAGAS evaluation
results = evaluate(
    dataset,
    llm=langchain_llm,
    metrics=[context_relevance, faithfulness, answer_relevance]
)
```

---

## 8. TESTING

### 8.1 Setup Verification

```bash
# Quick check
python test_gigachat.py
```

```python
# test_gigachat.py
from src.llm import create_llm_provider

def test_gigachat():
    provider = create_llm_provider()

    response = provider.generate(
        system_prompt="You are an assistant.",
        user_prompt="Say 'Hello' in Russian."
    )

    assert 'Hello' in response.content or 'Привет' in response.content
    assert response.metadata['provider'] == 'gigachat'
    print("GigaChat working correctly!")

if __name__ == '__main__':
    test_gigachat()
```

### 8.2 Unit Tests

```python
# tests/unit/test_gigachat_provider.py

import pytest
from src.llm.gigachat_provider import GigaChatProvider

class TestGigaChatProvider:

    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        config = LLMConfig(
            provider_type='gigachat',
            extra_params={'credentials': 'valid_key'}
        )
        provider = GigaChatProvider(config)
        assert provider.model == 'GigaChat-Pro'

    def test_init_without_credentials_raises(self):
        """Test error on missing credentials."""
        config = LLMConfig(provider_type='gigachat')
        with pytest.raises(ValueError):
            GigaChatProvider(config)

    @pytest.mark.integration
    def test_generate_returns_response(self):
        """Integration test for generation."""
        provider = create_llm_provider()
        response = provider.generate(
            system_prompt="Test",
            user_prompt="Say hello"
        )
        assert response.content
        assert 'model' in response.metadata
```

---

## 9. MONITORING

### 9.1 Metrics

```python
# Prometheus metrics
gigachat_requests_total = Counter(
    'gigachat_requests_total',
    'Total GigaChat API requests',
    ['method', 'status']
)

gigachat_request_duration = Histogram(
    'gigachat_request_duration_seconds',
    'GigaChat API request duration',
    ['method']
)

gigachat_tokens_used = Counter(
    'gigachat_tokens_used_total',
    'Total tokens used',
    ['type']  # prompt, completion
)
```

### 9.2 Logging

```python
import logging

logger = logging.getLogger('CodeGraph.gigachat')

# Request logging
logger.info(f"GigaChat request: model={model}, tokens={usage}")
logger.debug(f"System prompt: {system_prompt[:100]}...")
logger.error(f"GigaChat error: {error}")
```

---

## 10. SECURITY

### 10.1 Credentials Storage

```python
# Recommended - environment variables
import os
credentials = os.getenv('GIGACHAT_AUTH_KEY')

# NOT recommended - hardcode
credentials = "my_secret_key"  # BAD!
```

### 10.2 Input Validation

```python
def validate_prompt(prompt: str) -> str:
    """Validate prompt before sending."""
    if len(prompt) > 100000:
        raise ValueError("Prompt too long")

    # Sanitization
    prompt = prompt.strip()

    return prompt
```

---

## 11. DEPENDENCIES

### requirements.txt

```
# GigaChat integration
langchain-gigachat>=0.2.0
langchain-core>=0.3.0
gigachain>=0.2.0

# HTTP client
httpx>=0.24.0

# Configuration
pyyaml>=6.0
python-dotenv>=1.0.0
```

---

## 12. FAQ

### Q: How to get GIGACHAT_AUTH_KEY?

1. Register at https://developers.sber.ru/
2. Create a GigaChat API project
3. Get Authorization Key (base64-encoded)
4. Export: `export GIGACHAT_AUTH_KEY="your_key"`

### Q: Which model to choose?

- **Development**: GigaChat-2 (faster, cheaper)
- **Production**: GigaChat-2-Pro (optimal balance)
- **Critical tasks**: GigaChat-2-Max (maximum quality)

### Q: How to optimize prompts?

1. Use clear instructions in system_prompt
2. Structure expected response format
3. Limit context to relevant information
4. Test on different examples

### Q: What to do with rate limiting?

Provider automatically handles rate limits with exponential backoff.
If errors continue:
1. Check your plan limits
2. Add caching for frequent queries
3. Contact support for limit increase

---

*Document version: 1.0 | December 2024*
