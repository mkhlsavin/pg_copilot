# Интеграции

> Интеграции со сторонними сервисами для CodeGraph.


## Доступные интеграции

| Интеграция | Описание |
| --- | --- |
| Yandex AI Studio | Yandex Cloud AI Studio (YandexGPT, Qwen3) через API, совместимое с OpenAI |
| GigaChat | Интеграция с LLM Sber GigaChat |

## Добавление новых интеграций

Новые интеграции должны:
1. Реализовывать базовый интерфейс провайдера из `src/llm/base_provider.py`
2. Добавить конфигурацию в `config.yaml`
3. Быть задокументированными в этой папке

## Сопутствующая документация

- [Конфигурация LLM](../getting-started/en/CONFIGURATION.md)
- [Безопасность](../reference/en/SECURITY.md) - DLP и аудит для провайдеров LLM
