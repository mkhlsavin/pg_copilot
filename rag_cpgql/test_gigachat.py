"""
Скрипт проверки настройки GigaChat API

Проверяет:
1. Наличие переменной окружения GIGACHAT_AUTH_KEY
2. Конфигурацию в config.yaml
3. Установку GigaChat SDK
4. Возможность подключения к API (опционально)

Использование:
    python test_gigachat.py
"""

import os
import sys
from pathlib import Path


def check_auth_key():
    """Проверка переменной окружения GIGACHAT_AUTH_KEY."""
    print("1. Проверка GIGACHAT_AUTH_KEY")
    print("-" * 60)

    auth_key = os.getenv("GIGACHAT_AUTH_KEY")

    if auth_key:
        print("[OK] GIGACHAT_AUTH_KEY установлен")
        print(f"     Длина ключа: {len(auth_key)} символов")
        if len(auth_key) > 20:
            print(f"     Начало ключа: {auth_key[:20]}...")
        else:
            print(f"     Ключ: {auth_key}")

        # Проверка формата (обычно Base64)
        if auth_key.startswith("Basic "):
            print("     [OK] Формат ключа корректен (Basic ...)")
        else:
            print("     [WARN] Ключ не начинается с 'Basic ' - проверьте формат")

        return True
    else:
        print("[ERROR] GIGACHAT_AUTH_KEY НЕ установлен!")
        print()
        print("Установите через PowerShell:")
        print('  $env:GIGACHAT_AUTH_KEY = "YOUR_AUTHORIZATION_KEY"')
        print()
        print("Или создайте файл .env:")
        print('  GIGACHAT_AUTH_KEY=YOUR_AUTHORIZATION_KEY')
        return False


def check_config_yaml():
    """Проверка конфигурации в config.yaml."""
    print()
    print("2. Проверка config.yaml")
    print("-" * 60)

    config_path = Path("config.yaml")

    if not config_path.exists():
        print("[ERROR] config.yaml не найден в текущей директории")
        print(f"        Текущая директория: {Path.cwd()}")
        return False

    print("[OK] config.yaml найден")

    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Проверка структуры конфигурации
        if 'llm' not in config:
            print("[WARN] Секция 'llm' не найдена в config.yaml")
            print("       Добавьте конфигурацию GigaChat:")
            print_example_config()
            return False

        if 'gigachat' not in config['llm']:
            print("[WARN] Секция 'llm.gigachat' не найдена")
            print("       Добавьте параметры GigaChat:")
            print_example_config()
            return False

        # Проверка параметров GigaChat
        gigachat_cfg = config['llm']['gigachat']

        print("[OK] Конфигурация GigaChat найдена:")
        print(f"     Client ID: {gigachat_cfg.get('client_id', '[НЕ УСТАНОВЛЕН]')}")
        print(f"     Scope: {gigachat_cfg.get('scope', '[НЕ УСТАНОВЛЕН]')}")
        print(f"     Model: {gigachat_cfg.get('model', '[НЕ УСТАНОВЛЕН]')}")

        if gigachat_cfg.get('temperature'):
            print(f"     Temperature: {gigachat_cfg['temperature']}")
        if gigachat_cfg.get('max_tokens'):
            print(f"     Max Tokens: {gigachat_cfg['max_tokens']}")

        # Проверка обязательных параметров
        required_params = ['client_id', 'scope', 'model']
        missing = [p for p in required_params if not gigachat_cfg.get(p)]

        if missing:
            print(f"[WARN] Отсутствуют параметры: {', '.join(missing)}")
            return False

        return True

    except ImportError:
        print("[ERROR] PyYAML не установлен")
        print("        pip install pyyaml")
        return False
    except Exception as e:
        print(f"[ERROR] Ошибка чтения config.yaml: {e}")
        return False


def print_example_config():
    """Вывести пример конфигурации."""
    print()
    print("Пример конфигурации для config.yaml:")
    print()
    print("llm:")
    print("  provider: gigachat")
    print("  gigachat:")
    print('    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"')
    print('    scope: "GIGACHAT_API_PERS"')
    print('    model: "GigaChat-2-Pro"')
    print("    temperature: 0.7")
    print("    max_tokens: 2000")
    print()


def check_gigachat_sdk():
    """Проверка установки GigaChat SDK."""
    print()
    print("3. Проверка GigaChat SDK")
    print("-" * 60)

    try:
        import gigachat
        print(f"[OK] GigaChat SDK установлен")
        print(f"     Версия: {getattr(gigachat, '__version__', 'неизвестна')}")
        return True
    except ImportError:
        print("[ERROR] GigaChat SDK не установлен")
        print()
        print("Установите через pip:")
        print("  pip install gigachat")
        return False


def check_connection(auth_key, config):
    """Опциональная проверка подключения к API."""
    print()
    print("4. Проверка подключения к API (опционально)")
    print("-" * 60)

    try:
        from gigachat import GigaChat

        gigachat_cfg = config['llm']['gigachat']

        print("Подключение к GigaChat API...")

        client = GigaChat(
            credentials=auth_key,
            scope=gigachat_cfg['scope'],
            model=gigachat_cfg.get('model', 'GigaChat-2-Pro'),
            verify_ssl_certs=False  # Можно изменить на True для продакшена
        )

        # Простой тестовый запрос
        print("Отправка тестового запроса...")

        response = client.chat(messages=[
            {"role": "user", "content": "Привет! Ответь одним словом: работает?"}
        ])

        answer = response.choices[0].message.content

        print(f"[OK] Подключение успешно!")
        print(f"     Ответ от API: {answer[:100]}")
        return True

    except Exception as e:
        print(f"[WARN] Не удалось подключиться к API: {e}")
        print("       Это нормально, если API недоступен или ключ неверен")
        print("       Проверьте:")
        print("       1. Правильность Authorization Key")
        print("       2. Доступность API GigaChat")
        print("       3. Настройки прокси/firewall")
        return False


def main():
    """Основная функция проверки."""
    print()
    print("=" * 60)
    print("Проверка настройки GigaChat API")
    print("=" * 60)
    print()

    # Флаги успешности проверок
    checks = {
        'auth_key': False,
        'config': False,
        'sdk': False,
        'connection': False
    }

    # 1. Проверить переменную окружения
    checks['auth_key'] = check_auth_key()

    # 2. Проверить config.yaml
    checks['config'] = check_config_yaml()

    # 3. Проверить GigaChat SDK
    checks['sdk'] = check_gigachat_sdk()

    # 4. Попробовать подключиться к API (опционально)
    if checks['auth_key'] and checks['config'] and checks['sdk']:
        # Загрузить конфигурацию для подключения
        try:
            import yaml
            with open("config.yaml") as f:
                config = yaml.safe_load(f)

            auth_key = os.getenv("GIGACHAT_AUTH_KEY")
            checks['connection'] = check_connection(auth_key, config)
        except:
            pass

    # Итоговый отчёт
    print()
    print("=" * 60)
    print("Итоговый отчёт")
    print("=" * 60)
    print()

    total_checks = 3  # auth_key, config, sdk (connection опциональна)
    passed_checks = sum([checks['auth_key'], checks['config'], checks['sdk']])

    print(f"Обязательные проверки: {passed_checks}/{total_checks}")
    print()

    print(f"  [{'OK' if checks['auth_key'] else 'FAIL'}] GIGACHAT_AUTH_KEY")
    print(f"  [{'OK' if checks['config'] else 'FAIL'}] config.yaml")
    print(f"  [{'OK' if checks['sdk'] else 'FAIL'}] GigaChat SDK")

    if checks['connection']:
        print(f"  [OK] Подключение к API (опционально)")
    else:
        print(f"  [SKIP] Подключение к API (не проверялось)")

    print()

    if passed_checks == total_checks:
        print("[SUCCESS] Все обязательные проверки пройдены!")
        print()
        print("Вы можете использовать GigaChat API в проекте.")
        print()
        print("Пример использования:")
        print()
        print("  from gigachat import GigaChat")
        print('  import os')
        print()
        print('  auth_key = os.getenv("GIGACHAT_AUTH_KEY")')
        print('  client = GigaChat(credentials=auth_key, scope="GIGACHAT_API_PERS")')
        print()
        print('  response = client.chat(messages=[')
        print('      {"role": "user", "content": "Привет!"}')
        print('  ])')
        return 0
    else:
        print("[ERROR] Не все проверки пройдены!")
        print()
        print("Для настройки см. docs/GIGACHAT_SETUP.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
