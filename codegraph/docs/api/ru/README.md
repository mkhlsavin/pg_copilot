# Документация API

> Документация по REST API и WebSocket интерфейсу для CodeGraph.


## Справочник API

| Документ | Описание |
| --- | --- |
| REST API | Полный справочник HTTP API с примерами |
| WebSocket API | Интерфейс для потоковой передачи в реальном времени |

## Быстрый старт

```
# Запуск сервера API {#start-the-api-server}
python -m src.api.cli serve

# Проверка работоспособности API {#check-api-health}
curl http://localhost:8000/health

# Получение токена аутентификации {#get-auth-token}
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

## Аутентификация

Все конечные точки (кроме `/health`) требуют аутентификации с использованием JWT:

```
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/scenarios
```

## Сопутствующая документация

- [Начало работы](../getting-started/README.md)
- [Руководство пользователя TUI](../guides/en/TUI_USER_GUIDE.md)
- [Конфигурация](../getting-started/en/CONFIGURATION.md)
