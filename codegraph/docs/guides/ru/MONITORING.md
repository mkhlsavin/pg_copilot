# Руководство по мониторингу

В этом руководстве рассматриваются вопросы мониторинга, сбора метрик и проверки работоспособности CodeGraph в производственных средах.

## Содержание

- [Обзор](#overview)
- [Быстрый старт](#quick-start)
- [Включение метрик](#enable-metrics)
- [Сервер проверки работоспособности](#health-check-server)
- [Метрики Prometheus](#prometheus-metrics)
- [Доступные метрики](#available-metrics)
- [Интервалы гистограмм](#histogram-buckets)
- [Сбор метрик](#recording-metrics)
- [Декораторы](#decorators)
- [@track_execution](#track_execution)
- [@track_agent](#track_agent)
- [@track_scenario](#track_scenario)
- [Проверки работоспособности](#health-checks)
- [Статус работоспособности](#health-status)
- [Работоспособность компонентов](#component-health)
- [Пользовательские проверки работоспособности](#custom-health-checks)
- [Эндпоинты проверки состояния](#health-endpoints)
- [Структурированное логирование](#structured-logging)
- [Настройка](#setup)
- [Формат логов](#log-format)
- [Логирование с контекстом](#context-logging)
- [Панели Grafana](#grafana-dashboards)
- [Рекомендуемые панели](#recommended-panels)
- [Правила оповещений](#alert-rules)
- [Интеграция с Kubernetes](#kubernetes-integration)
- [Конфигурация развертывания](#deployment-configuration)
- [ServiceMonitor для Prometheus](#servicemonitor-for-prometheus)
- [Рекомендации](#best-practices)
- [Смотрите также](#see-also)

## Обзор

Модуль мониторинга предоставляет:
- **Метрики Prometheus** для отслеживания состояния системы
- **Структурированное JSON-логирование** для анализа
- **Эндпоинты проверки работоспособности** для оркестрации
- **Декораторы мониторинга** для инструментирования кода

---

## Быстрый старт

### Включение метрик

```
from src.monitoring import (
    MetricsCollector,
    track_execution,
    track_agent,
    setup_structured_logging
)

# Настройка структурированного логирования
setup_structured_logging(log_level="INFO")

# Получение сборщика метрик
metrics = MetricsCollector()

# Использование декораторов для автоматического отслеживания
@track_execution("my_operation")
def process_query(query: str):
    # Ваш код здесь
    return result
```

### Сервер проверки работоспособности

```
from src.monitoring.health import HealthCheckServer

# Запуск сервера проверки работоспособности (работает параллельно с основным приложением)
health_server = HealthCheckServer(port=8081)
health_server.start()

# Доступные конечные точки:
# GET /health    - Общий статус работоспособности
# GET /ready     - Проверка готовности
# GET /live      - Проверка активности
# GET /metrics   - Метрики Prometheus
# GET /stats     - Статистика системы
```

---

## Метрики Prometheus

### Доступные метрики

| Метрика | Тип | Метки | Описание |
| --- | --- | --- | --- |
| rag_scenario_duration_seconds | Гистограмма | scenario_name | Время выполнения сценария |
| rag_scenario_success_total | Счётчик | scenario_name | Успешные выполнения |
| rag_scenario_failure_total | Счётчик | scenario_name, error_type | Неудачные выполнения |
| rag_agent_duration_seconds | Гистограмма | agent_name, scenario | Время выполнения агента |
| rag_agent_success_total | Счётчик | agent_name, scenario | Успешные действия агента |
| rag_agent_failure_total | Счётчик | agent_name, scenario, error_type | Сбои агента |
| rag_cache_hits_total | Счётчик | cache_name | Попадания в кэш |
| rag_cache_misses_total | Счётчик | cache_name | Промахи кэша |
| rag_llm_requests_total | Счётчик | model, status | Запросы к API LLM |
| rag_llm_duration_seconds | Гистограмма | model | Задержка LLM |
| rag_llm_tokens_total | Счётчик | model, type | Использованные токены |
| rag_query_duration_seconds | Гистограмма | query_type | Время выполнения запроса к базе данных |
| rag_active_connections | Gauge | — | Активные соединения |

### Интервалы гистограмм (Buckets)

```
# Интервалы для времени выполнения сценария (секунды)
[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]

# Интервалы для времени выполнения агента (секунды)
[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

# Интервалы для времени выполнения запросов (миллисекунды)
[1, 5, 10, 25, 50, 100, 250, 500, 1000]
```

### Запись метрик

```
from src.monitoring.metrics import (
    SCENARIO_DURATION,
    SCENARIO_SUCCESS,
    SCENARIO_FAILURE,
    LLM_REQUESTS,
    LLM_DURATION,
    LLM_TOKENS
)

# Запись времени выполнения сценария
with SCENARIO_DURATION.labels(scenario_name="security_audit").time():
    result = run_scenario()

SCENARIO_SUCCESS.labels(scenario_name="security_audit").inc()

# Запись использования LLM
LLM_REQUESTS.labels(model="GigaChat-2-Pro", status="success").inc()
LLM_DURATION.labels(model="GigaChat-2-Pro").observe(2.5)
LLM_TOKENS.labels(model="GigaChat-2-Pro", type="completion").inc(150)
```

## Декораторы

### @track_execution

Автоматически отслеживает время выполнения функции и успешность/неудачу.

```
from src.monitoring import track_execution

@track_execution("data_processing")
def process_data(data: list) -> dict:
    # Автоматически записывает:
    # - Длительность в rag_operation_duration_seconds
    # - Успех/неудачу в rag_operation_total
    return processed_data

@track_execution("api_call", log_args=True)
def call_api(url: str, params: dict) -> dict:
    # Также логирует аргументы функции
    return response
```

### @track_agent

Отслеживает выполнение агента с контекстом сценария.

```
from src.monitoring import track_agent

@track_agent("analyzer")
def run_analyzer(question: str, scenario: str):
    # Записывает в метрики rag_agent_*
    return analysis
```

### @track_scenario

Отслеживает выполнение полного сценария.

```
from src.monitoring import track_scenario

@track_scenario("security_audit")
def run_security_audit(codebase: str):
    # Записывает в метрики rag_scenario_*
    return findings
```

## Проверки работоспособности

### Статус работоспособности

```
class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
```

### Работоспособность компонентов

Система проверяет следующие компоненты:

| Компонент | Проверка | Порог |
| --- | --- | --- |
| База данных | Задержка запроса | < 100 мс |
| Поставщик LLM | Ответ API | < 5 с |
| Векторное хранилище | Задержка запроса | < 200 мс |
| Кэш | Чтение/запись | < 50 мс |
| Joern | Подключение | < 1 с |

### Пользовательские проверки работоспособности

```
from src.monitoring.health import HealthChecker, ComponentHealth, HealthStatus

checker = HealthChecker()

# Добавление пользовательской проверки компонента
def check_custom_service():
    try:
        response_time = ping_service()
        if response_time < 100:
            return ComponentHealth(
                name="custom_service",
                status=HealthStatus.HEALTHY,
                latency_ms=response_time
            )
        else:
            return ComponentHealth(
                name="custom_service",
                status=HealthStatus.DEGRADED,
                latency_ms=response_time,
                message="Высокая задержка"
            )
    except Exception as e:
        return ComponentHealth(
            name="custom_service",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )

checker.add_check("custom_service", check_custom_service)
```

### Эндпоинты проверки состояния

**GET /health**

```
{
  "status": "healthy",
  "components": [
    {
      "name": "database",
      "status": "healthy",
      "latency_ms": 2.5,
      "message": ""
    },
    {
      "name": "llm_provider",
      "status": "healthy",
      "latency_ms": 450.0,
      "message": ""
    }
  ],
  "timestamp": 1702580000.0,
  "uptime_seconds": 3600.0,
  "version": "2.0.0"
}
```

**GET /ready**

```
{
  "ready": true,
  "checks_passed": 4,
  "checks_total": 4
}
```

**GET /live**

```
{
  "alive": true,
  "uptime_seconds": 3600.0
}
```

## Структурированное логирование

### Настройка

```
from src.monitoring import setup_structured_logging

# Настройка структурированного логирования
setup_structured_logging(
    log_level="INFO",
    json_format=True,
    include_timestamp=True,
    include_caller=True
)
```

### Формат лога

```
{
  "timestamp": "2025-12-14T10:30:00.000Z",
  "level": "INFO",
  "logger": "src.agents.analyzer",
  "message": "Запрос обработан",
  "context": {
    "scenario": "security_audit",
    "query_id": "abc123",
    "duration_ms": 245
  },
  "caller": {
    "file": "analyzer.py",
    "line": 45,
    "function": "process_query"
  }
}
```

### Логирование с контекстом

```
from src.monitoring import log_context, get_logger

logger = get_logger(__name__)

# Добавить контекст ко всем логам в текущей области видимости
with log_context(request_id="abc123", user_id="user1"):
    logger.info("Обработка запроса")  # Включает request_id и user_id

    result = process()

    logger.info("Запрос завершён", extra={"result_count": len(result)})
```

---

## Панели Grafana

### Рекомендуемые панели

**Частота запросов:**

```
rate(rag_scenario_success_total[5m]) + rate(rag_scenario_failure_total[5m])
```

**Частота ошибок:**

```
rate(rag_scenario_failure_total[5m]) / (rate(rag_scenario_success_total[5m]) + rate(rag_scenario_failure_total[5m]))
```

**Задержка P95:**

```
histogram_quantile(0.95, rate(rag_scenario_duration_seconds_bucket[5m]))
```

**Использование токенов СЯО (LLM):**

```
sum(rate(rag_llm_tokens_total[1h])) by (model)
```

**Процент попаданий в кэш:**

```
rate(rag_cache_hits_total[5m]) / (rate(rag_cache_hits_total[5m]) + rate(rag_cache_misses_total[5m]))
```

### Правила оповещений

```
groups:
  - name: codegraph
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(rag_scenario_failure_total[5m]))
          / sum(rate(rag_scenario_success_total[5m]) + rate(rag_scenario_failure_total[5m]))
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Обнаружена высокая частота ошибок"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(rag_scenario_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 задержка превышает 30 секунд"

      - alert: ComponentUnhealthy
        expr: rag_component_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Компонент {{ $labels.component }} неработоспособен"
```

## Интеграция с Kubernetes

### Конфигурация развертывания

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codegraph
spec:
  template:
    spec:
      containers:
        - name: codegraph
          ports:
            - containerPort: 8000
              name: api
            - containerPort: 8081
              name: health
          livenessProbe:
            httpGet:
              path: /live
              port: health
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: health
            initialDelaySeconds: 10
            periodSeconds: 5
```

### ServiceMonitor для Prometheus

```
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: codegraph
spec:
  selector:
    matchLabels:
      app: codegraph
  endpoints:
    - port: health
      path: /metrics
      interval: 30s
```

---

## Рекомендации

1. **Используйте декораторы** для автоматической инструментации
2. **Добавляйте контекст** в логи для обеспечения прослеживаемости
3. **Устанавливайте подходящие пороговые значения** для оповещений
4. **Отслеживайте использование токенов**, чтобы контролировать расходы
5. **Анализируйте задержки P95/P99**, а не только средние значения
6. **Экспортируйте метрики** в Prometheus для долговременного хранения
7. **Используйте структурированное логирование** для агрегации логов

---

## См. также

- [Справочник по REST API](../api/REST_API.md) — конечные точки API
- [Готовность к развертыванию](../development/DEPLOYMENT_READINESS_PLAN.md) — настройка для работы в продакшене
- [Документация Prometheus](https://prometheus.io/docs/)
- [Документация Grafana](https://grafana.com/docs/)
