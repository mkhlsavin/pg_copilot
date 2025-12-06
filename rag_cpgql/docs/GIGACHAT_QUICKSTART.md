# GigaChat - Быстрый старт 🚀

## Настройка за 3 шага

### Шаг 1: Установить Authorization Key

**PowerShell (одна команда):**
```powershell
$env:GIGACHAT_AUTH_KEY = "ВАШ_КЛЮЧ_АВТОРИЗАЦИИ"
```

**Для постоянной установки:**
```powershell
[System.Environment]::SetEnvironmentVariable('GIGACHAT_AUTH_KEY', 'ВАШ_КЛЮЧ', 'User')
```

---

### Шаг 2: Добавить параметры в config.yaml

```yaml
llm:
  provider: "gigachat"

  gigachat:
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"
    temperature: 0.7
    max_tokens: 2000
```

**Или скопировать готовый шаблон:**
```powershell
copy config.gigachat.yaml.example config.yaml
```

---

### Шаг 3: Проверить настройку

```powershell
python test_gigachat.py
```

**Ожидаемый результат:**
```
============================================================
Проверка настройки GigaChat API
============================================================

1. Проверка GIGACHAT_AUTH_KEY
------------------------------------------------------------
[OK] GIGACHAT_AUTH_KEY установлен
     Длина ключа: 156 символов
     Начало ключа: Basic Y2xpZW50X2...

2. Проверка config.yaml
------------------------------------------------------------
[OK] config.yaml найден
[OK] Конфигурация GigaChat найдена:
     Client ID: 019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6
     Scope: GIGACHAT_API_PERS
     Model: GigaChat-2-Pro

3. Проверка GigaChat SDK
------------------------------------------------------------
[OK] GigaChat SDK установлен

============================================================
[SUCCESS] Все обязательные проверки пройдены!
============================================================
```

---

## Использование

### Пример 1: Простой запрос

```python
import os
from gigachat import GigaChat

# Получить ключ из переменной окружения
auth_key = os.getenv("GIGACHAT_AUTH_KEY")

# Создать клиента
client = GigaChat(
    credentials=auth_key,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2-Pro"
)

# Отправить запрос
response = client.chat(messages=[
    {"role": "user", "content": "Привет! Как дела?"}
])

print(response.choices[0].message.content)
```

### Пример 2: Использование с конфигурацией

```python
import os
import yaml
from gigachat import GigaChat
from pathlib import Path

# Загрузить конфигурацию
with open("config.yaml") as f:
    config = yaml.safe_load(f)

gigachat_cfg = config['llm']['gigachat']

# Получить ключ
auth_key = os.getenv("GIGACHAT_AUTH_KEY")

# Создать клиента с параметрами из конфига
client = GigaChat(
    credentials=auth_key,
    scope=gigachat_cfg['scope'],
    model=gigachat_cfg['model'],
    verify_ssl_certs=gigachat_cfg.get('verify_ssl_certs', False)
)

# Использование
response = client.chat(
    messages=[{"role": "user", "content": "Объясни MVCC в PostgreSQL"}],
    temperature=gigachat_cfg.get('temperature', 0.7),
    max_tokens=gigachat_cfg.get('max_tokens', 2000)
)

print(response.choices[0].message.content)
```

---

## Параметры

### Ваши параметры:

| Параметр | Значение |
|----------|----------|
| Client ID | `019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6` |
| Scope | `GIGACHAT_API_PERS` |
| Model | `GigaChat-2-Pro` |
| Auth Key | `[в переменной окружения]` |

### Доступные модели:

| Модель | Описание |
|--------|----------|
| `GigaChat-2-Pro` | Самая мощная модель (рекомендуется) |
| `GigaChat-Plus` | Расширенная версия |
| `GigaChat` | Базовая версия |

---

## Проверка установки

### Проверить переменную окружения:

```powershell
echo $env:GIGACHAT_AUTH_KEY
```

### Проверить всю настройку:

```powershell
python test_gigachat.py
```

---

## Установка SDK (если нужно)

```bash
pip install gigachat
```

Или добавить в `requirements.txt`:
```txt
gigachat>=0.1.0
```

---

## Устранение проблем

### Проблема: "GIGACHAT_AUTH_KEY не установлен"

**Решение:**
```powershell
# Установить в текущей сессии
$env:GIGACHAT_AUTH_KEY = "ВАШ_КЛЮЧ"

# Проверить
echo $env:GIGACHAT_AUTH_KEY
```

### Проблема: "Ключ не работает"

**Проверить формат ключа:**
- Должен начинаться с `Basic `
- Длина обычно 100+ символов
- Формат Base64

**Пример правильного ключа:**
```
Basic Y2xpZW50X2lkOmNsaWVudF9zZWNyZXQ...
```

### Проблема: "Не могу подключиться к API"

**Проверить:**
1. Правильность ключа авторизации
2. Доступность API: https://gigachat.devices.sberbank.ru
3. Настройки прокси/firewall
4. SSL сертификаты (попробуйте `verify_ssl_certs: false`)

---

## Полезные ссылки

- 📖 **Полная инструкция:** `docs/GIGACHAT_SETUP.md`
- 🧪 **Скрипт проверки:** `test_gigachat.py`
- ⚙️ **Шаблон конфига:** `config.gigachat.yaml.example`
- 📚 **Официальная документация:** https://developers.sber.ru/docs/ru/gigachat/

---

## Чеклист

- [ ] Установил `GIGACHAT_AUTH_KEY` через PowerShell
- [ ] Добавил параметры GigaChat в `config.yaml`
- [ ] Установил GigaChat SDK: `pip install gigachat`
- [ ] Запустил `python test_gigachat.py`
- [ ] Получил "[SUCCESS] Все проверки пройдены!"

---

**Готово!** 🎉 Теперь можно использовать GigaChat API.

Для более подробной информации см. `docs/GIGACHAT_SETUP.md`
