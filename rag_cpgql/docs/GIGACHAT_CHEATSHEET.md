# GigaChat API - Шпаргалка ⚡

## Быстрые команды

### Установка ключа (PowerShell)

```powershell
# Текущая сессия
$env:GIGACHAT_AUTH_KEY = "YOUR_KEY"

# Постоянно
[System.Environment]::SetEnvironmentVariable('GIGACHAT_AUTH_KEY', 'YOUR_KEY', 'User')

# Проверить
echo $env:GIGACHAT_AUTH_KEY
```

### Автоматическая настройка

```powershell
.\setup_gigachat.ps1
```

### Проверка настройки

```powershell
python test_gigachat.py
```

---

## Ваши параметры

```yaml
Client ID: 019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6
Scope:     GIGACHAT_API_PERS
Model:     GigaChat-2-Pro
Auth Key:  [в $env:GIGACHAT_AUTH_KEY]
```

---

## Минимальный код

### Python

```python
import os
from gigachat import GigaChat

client = GigaChat(
    credentials=os.getenv("GIGACHAT_AUTH_KEY"),
    scope="GIGACHAT_API_PERS"
)

response = client.chat(messages=[
    {"role": "user", "content": "Привет!"}
])

print(response.choices[0].message.content)
```

### Config.yaml

```yaml
llm:
  provider: gigachat
  gigachat:
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"
```

---

## Доступные модели

| Модель | Описание |
|--------|----------|
| `GigaChat-2-Pro` | Самая мощная ⭐ |
| `GigaChat-Plus` | Расширенная |
| `GigaChat` | Базовая |

---

## Файлы

| Файл | Описание |
|------|----------|
| `GIGACHAT_QUICKSTART.md` | Быстрый старт (3 шага) |
| `docs/GIGACHAT_SETUP.md` | Полная инструкция |
| `test_gigachat.py` | Скрипт проверки |
| `setup_gigachat.ps1` | Автоматическая настройка |
| `config.gigachat.yaml.example` | Шаблон конфигурации |

---

## Устранение проблем

| Проблема | Решение |
|----------|---------|
| Ключ не установлен | `$env:GIGACHAT_AUTH_KEY = "KEY"` |
| SDK не установлен | `pip install gigachat` |
| Ошибка SSL | `verify_ssl_certs: false` в config.yaml |
| Ключ не работает | Проверить формат: должен начинаться с `Basic ` |

---

## Полезные ссылки

- 📘 [Официальная документация](https://developers.sber.ru/docs/ru/gigachat/)
- 🚀 [Быстрый старт](GIGACHAT_QUICKSTART.md)
- 📖 [Полная инструкция](docs/GIGACHAT_SETUP.md)

---

**Готово к использованию!** 🎉
