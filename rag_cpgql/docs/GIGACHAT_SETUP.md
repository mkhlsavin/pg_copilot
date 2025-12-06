# Настройка GigaChat API

**Дата:** 25 ноября 2025

---

## Быстрая настройка

### Способ 1: PowerShell (Рекомендуется для разработки)

Установите переменную окружения в текущей сессии PowerShell:

```powershell
# Установить Authorization Key
$env:GIGACHAT_AUTH_KEY = "YOUR_AUTHORIZATION_KEY_HERE"

# Проверить установку
echo $env:GIGACHAT_AUTH_KEY

# Запустить приложение
python your_script.py
```

**Для постоянной установки (сохраняется после перезагрузки):**

```powershell
# Установить для текущего пользователя
[System.Environment]::SetEnvironmentVariable('GIGACHAT_AUTH_KEY', 'YOUR_AUTHORIZATION_KEY_HERE', 'User')

# Проверить
[System.Environment]::GetEnvironmentVariable('GIGACHAT_AUTH_KEY', 'User')
```

---

### Способ 2: Файл `.env` (Рекомендуется для продакшена)

1. **Создайте файл `.env` в корне проекта:**

```bash
# .env
GIGACHAT_AUTH_KEY=YOUR_AUTHORIZATION_KEY_HERE
```

2. **Файл `.env` уже в `.gitignore`** - секреты не попадут в Git ✓

---

## Параметры GigaChat

### Ваши параметры:

| Параметр | Значение |
|----------|----------|
| **ClientID** | `019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6` |
| **Scope** | `GIGACHAT_API_PERS` |
| **Model** | `GigaChat-2-Pro` |
| **Auth Key** | `[установить в переменной окружения]` |

---

## Конфигурация в проекте

### Добавьте параметры в `config.yaml`:

```yaml
llm:
  provider: "gigachat"  # вместо "openai" или "anthropic"

  gigachat:
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"
    # auth_key читается из переменной окружения GIGACHAT_AUTH_KEY

    # Дополнительные параметры (опционально)
    temperature: 0.7
    max_tokens: 2000
    timeout: 60
```

---

## Использование в коде

### Пример инициализации LLM с GigaChat:

```python
import os
from pathlib import Path
import yaml

# Загрузить конфигурацию
config_path = Path("config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Получить Authorization Key из переменной окружения
auth_key = os.getenv("GIGACHAT_AUTH_KEY")

if not auth_key:
    raise ValueError(
        "GIGACHAT_AUTH_KEY не установлен!\n"
        "Установите через PowerShell:\n"
        "$env:GIGACHAT_AUTH_KEY = 'YOUR_KEY'"
    )

# Параметры из config.yaml
gigachat_config = config['llm']['gigachat']

# Инициализация GigaChat клиента
from gigachat import GigaChat

client = GigaChat(
    credentials=auth_key,
    scope=gigachat_config['scope'],
    model=gigachat_config['model'],
    verify_ssl_certs=False  # если нужно отключить проверку SSL
)

# Использование
response = client.chat(messages=[
    {"role": "user", "content": "Привет!"}
])

print(response.choices[0].message.content)
```

---

## Проверка настройки

### Скрипт для проверки:

Создайте файл `test_gigachat.py`:

```python
import os
import sys

def check_gigachat_setup():
    """Проверка настройки GigaChat API."""

    print("=" * 60)
    print("Проверка настройки GigaChat API")
    print("=" * 60)
    print()

    # 1. Проверить переменную окружения
    auth_key = os.getenv("GIGACHAT_AUTH_KEY")

    if auth_key:
        print(f"✓ GIGACHAT_AUTH_KEY установлен")
        print(f"  Длина ключа: {len(auth_key)} символов")
        print(f"  Первые 10 символов: {auth_key[:10]}...")
    else:
        print("✗ GIGACHAT_AUTH_KEY НЕ установлен!")
        print()
        print("Установите через PowerShell:")
        print('  $env:GIGACHAT_AUTH_KEY = "YOUR_KEY"')
        sys.exit(1)

    print()

    # 2. Проверить config.yaml
    try:
        import yaml
        from pathlib import Path

        config_path = Path("config.yaml")

        if config_path.exists():
            print("✓ config.yaml найден")

            with open(config_path) as f:
                config = yaml.safe_load(f)

            if 'llm' in config and 'gigachat' in config['llm']:
                gigachat_cfg = config['llm']['gigachat']
                print(f"  ClientID: {gigachat_cfg.get('client_id', 'НЕ УСТАНОВЛЕН')}")
                print(f"  Scope: {gigachat_cfg.get('scope', 'НЕ УСТАНОВЛЕН')}")
                print(f"  Model: {gigachat_cfg.get('model', 'НЕ УСТАНОВЛЕН')}")
            else:
                print("  ⚠ Секция llm.gigachat не найдена в config.yaml")
        else:
            print("✗ config.yaml не найден")
    except Exception as e:
        print(f"✗ Ошибка чтения config.yaml: {e}")

    print()

    # 3. Попробовать импортировать GigaChat SDK
    try:
        import gigachat
        print(f"✓ GigaChat SDK установлен (версия: {gigachat.__version__})")
    except ImportError:
        print("✗ GigaChat SDK не установлен")
        print()
        print("Установите через pip:")
        print("  pip install gigachat")

    print()
    print("=" * 60)
    print("Проверка завершена")
    print("=" * 60)

if __name__ == "__main__":
    check_gigachat_setup()
```

**Запуск проверки:**

```powershell
python test_gigachat.py
```

---

## Установка GigaChat SDK

Если SDK ещё не установлен:

```bash
pip install gigachat
```

Или добавьте в `requirements.txt`:

```txt
gigachat>=0.1.0
```

---

## Безопасность

### ✓ Правильно (секреты в переменных окружения):

```powershell
# В PowerShell
$env:GIGACHAT_AUTH_KEY = "your_secret_key"

# В Python
auth_key = os.getenv("GIGACHAT_AUTH_KEY")
```

### ✗ Неправильно (секреты в коде):

```python
# НЕ ДЕЛАЙТЕ ТАК!
auth_key = "your_secret_key"  # ❌ Попадёт в Git!
```

### ✓ Файл `.env` уже в `.gitignore`:

```gitignore
# .gitignore (уже есть)
.env
*.env
.env.*
```

---

## Полный пример настройки (шаг за шагом)

### Шаг 1: Установить переменную окружения

```powershell
# В PowerShell
$env:GIGACHAT_AUTH_KEY = "ваш_реальный_ключ_авторизации"
```

### Шаг 2: Добавить конфигурацию в `config.yaml`

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

### Шаг 3: Проверить установку

```powershell
python test_gigachat.py
```

### Шаг 4: Использовать в коде

```python
import os
from gigachat import GigaChat

auth_key = os.getenv("GIGACHAT_AUTH_KEY")
client = GigaChat(credentials=auth_key, scope="GIGACHAT_API_PERS")

response = client.chat(messages=[
    {"role": "user", "content": "Привет!"}
])
```

---

## Часто задаваемые вопросы

### Q: Где взять Authorization Key?

A: Authorization Key выдаётся в личном кабинете GigaChat при регистрации приложения. Это Base64-encoded строка вида `Basic <credentials>`.

### Q: Нужно ли устанавливать ClientID отдельно?

A: Нет, ClientID уже включён в конфигурацию `config.yaml`. Достаточно установить только `GIGACHAT_AUTH_KEY`.

### Q: Как проверить, что ключ работает?

A: Запустите скрипт `test_gigachat.py` для проверки настройки и подключения.

### Q: Можно ли использовать .env файл вместо PowerShell?

A: Да! Создайте файл `.env` с `GIGACHAT_AUTH_KEY=your_key` и используйте библиотеку `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()

auth_key = os.getenv("GIGACHAT_AUTH_KEY")
```

---

## Итоговый чеклист

- [ ] Установил `GIGACHAT_AUTH_KEY` через PowerShell или `.env`
- [ ] Добавил параметры GigaChat в `config.yaml`
- [ ] Установил GigaChat SDK: `pip install gigachat`
- [ ] Запустил `test_gigachat.py` для проверки
- [ ] Проверил, что `.env` в `.gitignore`

---

## Поддержка

Если возникли проблемы:
1. Проверьте, что `GIGACHAT_AUTH_KEY` установлен: `echo $env:GIGACHAT_AUTH_KEY`
2. Проверьте формат ключа (должен начинаться с `Basic `)
3. Проверьте подключение к API GigaChat
4. Запустите `test_gigachat.py` для диагностики

---

**Готово!** Теперь можно использовать GigaChat API в проекте.
