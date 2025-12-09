# CodeGraph: Техническая интеграция GigaChat

## Обзор

Данный документ описывает техническую архитектуру интеграции GigaChat в систему CodeGraph — AI-копилот для анализа исходного кода.

---

## 1. АРХИТЕКТУРА ИНТЕГРАЦИИ

### 1.1 LLM Provider Layer

```
┌─────────────────────────────────────────────────────────┐
│              LLM Provider Interface                     │
│           src/llm/base_provider.py                      │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
     ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
     │  Local  │   │ GigaChat│   │ OpenAI  │
     │ (llama) │   │ Provider│   │ Provider│
     └─────────┘   └─────────┘   └─────────┘
                        │
                        ▼
              ┌─────────────────┐
              │ LangChain       │
              │ Adapter         │
              │ (для RAGAS)     │
              └─────────────────┘
```

### 1.2 Ключевые файлы

| Файл | Назначение | Строк кода |
|------|------------|------------|
| `src/llm/gigachat_provider.py` | Основной провайдер GigaChat | 431 |
| `src/llm/factory.py` | Фабрика провайдеров | 150 |
| `src/llm/base_provider.py` | Базовый интерфейс | 120 |
| `src/llm/langchain_adapter.py` | Адаптер для RAGAS | 80 |
| `src/evaluation/ragas_config.py` | Конфигурация RAGAS | 200 |

---

## 2. GIGACHAT PROVIDER

### 2.1 Инициализация

```python
from src.llm.gigachat_provider import GigaChatProvider
from src.llm.base_provider import LLMConfig
import os

# Конфигурация
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

# Создание провайдера
provider = GigaChatProvider(config)
```

### 2.2 Основные методы

#### generate() — Основной метод генерации

```python
def generate(
    self,
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> LLMResponse:
    """
    Генерация ответа с разделением на system/user промпты.

    Args:
        system_prompt: Системный промпт (роль, инструкции)
        user_prompt: Пользовательский запрос
        **kwargs: Дополнительные параметры (temperature, max_tokens)

    Returns:
        LLMResponse с полями:
            - content: str - сгенерированный текст
            - metadata: dict - информация о вызове
    """
```

**Пример использования:**

```python
response = provider.generate(
    system_prompt="""Вы — эксперт по анализу кода PostgreSQL.
    Анализируйте вопросы и определяйте intent.""",
    user_prompt="Найди SQL injection уязвимости"
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

#### generate_simple() — Простая генерация

```python
def generate_simple(self, prompt: str, **kwargs) -> LLMResponse:
    """
    Простая генерация без разделения на system/user.
    Отправляет prompt как HumanMessage.
    """
```

#### generate_stream() — Потоковая генерация

```python
def generate_stream(
    self,
    system_prompt: str,
    user_prompt: str,
    **kwargs
) -> Generator[str, None, None]:
    """
    Streaming generation для длинных ответов.
    Использует client.stream() для чанков.

    Yields:
        str: Чанки текста по мере получения
    """
```

**Пример:**

```python
for chunk in provider.generate_stream(
    system_prompt="Вы — эксперт по PostgreSQL",
    user_prompt="Объясни механизм MVCC подробно"
):
    print(chunk, end='', flush=True)
```

---

## 3. КОНФИГУРАЦИЯ

### 3.1 config.yaml

```yaml
llm:
  # Выбор провайдера: "gigachat", "local", "openai"
  provider: "gigachat"

  gigachat:
    # Идентификатор клиента (опционально)
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"

    # Авторизационный ключ (из переменной окружения)
    credentials: ${GIGACHAT_AUTH_KEY}

    # Модель
    # Варианты: "GigaChat-2", "GigaChat-2-Pro", "GigaChat-2-Max"
    model: "GigaChat-2-Pro"

    # Кастомный endpoint (опционально)
    base_url: null

    # SSL верификация
    # false для разработки, true для production
    verify_ssl_certs: true

    # Область доступа
    # Варианты: GIGACHAT_API_PERS, GIGACHAT_API_CORP, GIGACHAT_API_B2B
    scope: "GIGACHAT_API_PERS"

    # Таймаут запроса (секунды)
    timeout: 60

    # Параметры генерации
    temperature: 0.7
    max_tokens: 2000
    top_p: null  # Использовать default GigaChat
```

### 3.2 Переменные окружения

```bash
# Обязательные
export GIGACHAT_AUTH_KEY="your_base64_encoded_key"

# Опциональные
export GIGACHAT_CLIENT_ID="019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
export GIGACHAT_SCOPE="GIGACHAT_API_PERS"
export GIGACHAT_MODEL="GigaChat-2-Pro"
```

### 3.3 Поддерживаемые модели

| Модель | Описание | Рекомендация |
|--------|----------|--------------|
| GigaChat-2 | Базовая модель v2 | Development, быстрые запросы |
| GigaChat-2-Pro | Продвинутая v2 | **Production (основная)** |
| GigaChat-2-Max | Максимальное качество | Критичные задачи |
| GigaChat | Legacy базовая | Совместимость |
| GigaChat-Pro | Legacy продвинутая | Совместимость |
| GigaChat-Plus | Legacy расширенная | Совместимость |

---

## 4. ОБРАБОТКА ОШИБОК

### 4.1 Rate Limiting

```python
# Константы retry-логики
MAX_RETRIES = 5
BASE_RETRY_DELAY = 2.0  # секунды
MAX_RETRY_DELAY = 60.0  # секунды

def _is_rate_limit_error(error: Exception) -> bool:
    """Определяет, является ли ошибка rate limit."""
    error_msg = str(error).lower()
    return any(phrase in error_msg for phrase in [
        '429', 'rate limit', 'too many requests'
    ])

def _retry_with_backoff(func, *args, **kwargs):
    """
    Exponential backoff с jitter.

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

### 4.2 Типы исключений

```python
class GigaChatProviderError(Exception):
    """Базовое исключение провайдера."""
    pass

class GigaChatAuthError(GigaChatProviderError):
    """Ошибка авторизации."""
    pass

class GigaChatRateLimitError(GigaChatProviderError):
    """Превышен лимит запросов."""
    pass

class GigaChatAPIError(GigaChatProviderError):
    """Общая ошибка API."""
    pass
```

---

## 5. ИСПОЛЬЗОВАНИЕ В АГЕНТАХ

### 5.1 Analyzer Agent

```python
# src/agents/analyzer_agent.py

class AnalyzerAgent:
    """Агент анализа intent пользовательского запроса."""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def analyze(self, question: str) -> AnalysisResult:
        system_prompt = """Вы — эксперт по анализу запросов к кодовой базе.
        Определите:
        1. Intent: find-function, explain-concept, security-check, etc.
        2. Keywords: ключевые термины для поиска
        3. Domain: vacuum, wal, mvcc, query-planning, memory, etc.
        4. Confidence: уверенность в классификации (0-1)
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
    """Агент генерации CPGQL запросов."""

    def generate_query(self, context: str, question: str) -> str:
        system_prompt = """Вы — эксперт по CPGQL (Code Property Graph Query Language).
        На основе контекста сгенерируйте CPGQL-запрос для DuckDB.

        Доступные таблицы:
        - nodes_method: id, name, signature, filename, line_number
        - edges_call: src, dst, call_line
        - tags: entity_id, tag_name, tag_value

        Формат ответа: только CPGQL-запрос без объяснений.
        """

        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=f"Контекст:\n{context}\n\nВопрос: {question}"
        )

        return self._clean_query(response.content)
```

### 5.3 Interpreter Agent

```python
# src/agents/interpreter_agent.py

class InterpreterAgent:
    """Агент интерпретации результатов."""

    def interpret(self, question: str, results: list) -> str:
        system_prompt = """Вы — эксперт по объяснению результатов анализа кода.
        Синтезируйте результаты запроса в понятный ответ на русском языке.

        Правила:
        1. Группируйте по категориям (Critical/High/Medium/Low для уязвимостей)
        2. Указывайте точные пути к файлам и номера строк
        3. Давайте рекомендации по исправлению
        4. Используйте маркированные списки для структуры
        """

        response = self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=f"Вопрос: {question}\n\nРезультаты:\n{json.dumps(results, ensure_ascii=False)}"
        )

        return response.content
```

---

## 6. FACTORY PATTERN

### 6.1 Создание провайдера

```python
# src/llm/factory.py

def create_llm_provider(config: dict = None) -> BaseLLMProvider:
    """
    Фабричный метод создания LLM провайдера.

    Args:
        config: Конфигурация (если None, загружается из config.yaml)

    Returns:
        Инстанс провайдера (GigaChatProvider, LocalProvider, etc.)
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
    """Создаёт GigaChat провайдер из конфигурации."""
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

### 6.2 Использование

```python
from src.llm import create_llm_provider

# Автоматическая загрузка из config.yaml
provider = create_llm_provider()

# Или с кастомной конфигурацией
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

### 7.1 Интеграция с RAGAS

```python
# src/llm/langchain_adapter.py

from langchain_core.language_models import BaseLLM

class LangChainGigaChatAdapter(BaseLLM):
    """Адаптер для совместимости с LangChain/RAGAS."""

    provider: GigaChatProvider

    def _call(self, prompt: str, **kwargs) -> str:
        response = self.provider.generate_simple(prompt, **kwargs)
        return response.content

    @property
    def _llm_type(self) -> str:
        return "gigachat"

def create_langchain_adapter(provider: BaseLLMProvider) -> BaseLLM:
    """Создаёт LangChain-совместимый адаптер."""
    return LangChainGigaChatAdapter(provider=provider)
```

### 7.2 Использование с RAGAS

```python
from ragas import evaluate
from src.llm import create_llm_provider, create_langchain_adapter

# Создаём провайдер и адаптер
provider = create_llm_provider()
langchain_llm = create_langchain_adapter(provider)

# Оценка с RAGAS
results = evaluate(
    dataset,
    llm=langchain_llm,
    metrics=[context_relevance, faithfulness, answer_relevance]
)
```

---

## 8. ТЕСТИРОВАНИЕ

### 8.1 Проверка настройки

```bash
# Быстрая проверка
python test_gigachat.py
```

```python
# test_gigachat.py
from src.llm import create_llm_provider

def test_gigachat():
    provider = create_llm_provider()

    response = provider.generate(
        system_prompt="Вы — ассистент.",
        user_prompt="Скажи 'Привет' на русском."
    )

    assert 'Привет' in response.content
    assert response.metadata['provider'] == 'gigachat'
    print("GigaChat работает корректно!")

if __name__ == '__main__':
    test_gigachat()
```

### 8.2 Unit тесты

```python
# tests/unit/test_gigachat_provider.py

import pytest
from src.llm.gigachat_provider import GigaChatProvider

class TestGigaChatProvider:

    def test_init_with_valid_credentials(self):
        """Тест инициализации с валидными credentials."""
        config = LLMConfig(
            provider_type='gigachat',
            extra_params={'credentials': 'valid_key'}
        )
        provider = GigaChatProvider(config)
        assert provider.model == 'GigaChat-Pro'

    def test_init_without_credentials_raises(self):
        """Тест ошибки при отсутствии credentials."""
        config = LLMConfig(provider_type='gigachat')
        with pytest.raises(ValueError):
            GigaChatProvider(config)

    @pytest.mark.integration
    def test_generate_returns_response(self):
        """Интеграционный тест генерации."""
        provider = create_llm_provider()
        response = provider.generate(
            system_prompt="Test",
            user_prompt="Say hello"
        )
        assert response.content
        assert 'model' in response.metadata
```

---

## 9. МОНИТОРИНГ

### 9.1 Метрики

```python
# Prometheus метрики
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

### 9.2 Логирование

```python
import logging

logger = logging.getLogger('CodeGraph.gigachat')

# Логирование запросов
logger.info(f"GigaChat request: model={model}, tokens={usage}")
logger.debug(f"System prompt: {system_prompt[:100]}...")
logger.error(f"GigaChat error: {error}")
```

---

## 10. БЕЗОПАСНОСТЬ

### 10.1 Хранение credentials

```python
# Рекомендуемый способ - переменные окружения
import os
credentials = os.getenv('GIGACHAT_AUTH_KEY')

# НЕ рекомендуется - хардкод
credentials = "my_secret_key"  # ПЛОХО!
```

### 10.2 Валидация входных данных

```python
def validate_prompt(prompt: str) -> str:
    """Валидация промпта перед отправкой."""
    if len(prompt) > 100000:
        raise ValueError("Prompt too long")

    # Санитизация
    prompt = prompt.strip()

    return prompt
```

---

## 11. ЗАВИСИМОСТИ

### requirements.txt

```
# GigaChat интеграция
langchain-gigachat>=0.2.0
langchain-core>=0.3.0
gigachain>=0.2.0

# HTTP клиент
httpx>=0.24.0

# Конфигурация
pyyaml>=6.0
python-dotenv>=1.0.0
```

---

## 12. FAQ

### Q: Как получить GIGACHAT_AUTH_KEY?

1. Зарегистрируйтесь на https://developers.sber.ru/
2. Создайте проект GigaChat API
3. Получите Authorization Key (base64-encoded)
4. Экспортируйте: `export GIGACHAT_AUTH_KEY="your_key"`

### Q: Какую модель выбрать?

- **Development**: GigaChat-2 (быстрее, дешевле)
- **Production**: GigaChat-2-Pro (оптимальный баланс)
- **Критичные задачи**: GigaChat-2-Max (максимальное качество)

### Q: Как оптимизировать промпты?

1. Используйте чёткие инструкции в system_prompt
2. Структурируйте ожидаемый формат ответа
3. Ограничивайте контекст релевантной информацией
4. Тестируйте на разных примерах

### Q: Что делать при rate limiting?

Провайдер автоматически обрабатывает rate limits с exponential backoff.
Если ошибки продолжаются:
1. Проверьте лимиты вашего тарифа
2. Добавьте caching для частых запросов
3. Обратитесь в поддержку за увеличением лимитов

---

*Версия документа: 1.0 | Декабрь 2024*
