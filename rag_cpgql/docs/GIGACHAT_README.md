# GigaChat API - Полная документация

**Дата:** 25 ноября 2025
**Версия:** 1.0

---

## 📚 Содержание документации

Для вашего удобства создана полная документация по настройке и использованию GigaChat API в проекте RAG-CPGQL.

### Документы по уровню детализации

| Документ | Описание | Для кого |
|----------|----------|----------|
| **[GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md)** | Шпаргалка с быстрыми командами | Опытные пользователи |
| **[GIGACHAT_QUICKSTART.md](../GIGACHAT_QUICKSTART.md)** | Быстрый старт за 3 шага | Начинающие |
| **[GIGACHAT_SETUP.md](GIGACHAT_SETUP.md)** | Полная инструкция со всеми деталями | Все пользователи |

### Вспомогательные файлы

| Файл | Тип | Назначение |
|------|-----|------------|
| `test_gigachat.py` | Python | Скрипт проверки настройки |
| `setup_gigachat.ps1` | PowerShell | Автоматическая настройка |
| `config.gigachat.yaml.example` | YAML | Шаблон конфигурации |

---

## 🚀 Как начать работу

### Вариант 1: Автоматическая настройка (рекомендуется)

```powershell
# Запустить скрипт автоматической настройки
.\setup_gigachat.ps1
```

Скрипт проведёт вас через все шаги:
1. Установка Authorization Key
2. Создание config.yaml из шаблона
3. Установка GigaChat SDK
4. Проверка настройки

### Вариант 2: Ручная настройка (3 шага)

#### Шаг 1: Установить ключ

```powershell
$env:GIGACHAT_AUTH_KEY = "ваш_ключ_авторизации"
```

#### Шаг 2: Настроить config.yaml

```yaml
llm:
  provider: gigachat
  gigachat:
    client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
    scope: "GIGACHAT_API_PERS"
    model: "GigaChat-2-Pro"
```

#### Шаг 3: Проверить

```powershell
python test_gigachat.py
```

### Вариант 3: Быстрая справка

Откройте **[GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md)** для быстрого доступа к ключевым командам.

---

## 📖 Структура документации

### Уровень 1: Шпаргалка (1 минута)

**Файл:** [GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md)

**Содержимое:**
- Быстрые команды PowerShell
- Ваши параметры (Client ID, Scope, Model)
- Минимальный код
- Доступные модели
- Устранение проблем

**Когда использовать:**
- Нужно быстро вспомнить команду
- Уже настраивали ранее
- Знакомы с GigaChat API

### Уровень 2: Быстрый старт (5 минут)

**Файл:** [GIGACHAT_QUICKSTART.md](../GIGACHAT_QUICKSTART.md)

**Содержимое:**
- Настройка за 3 шага
- Примеры использования
- Таблица параметров
- Чеклист настройки
- Основные проблемы и решения

**Когда использовать:**
- Первая настройка GigaChat
- Нужна пошаговая инструкция
- Хотите быстро начать работу

### Уровень 3: Полная инструкция (15 минут)

**Файл:** [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md)

**Содержимое:**
- Детальная инструкция по настройке
- 2 способа установки (PowerShell + .env)
- Конфигурация в проекте
- Примеры использования в коде
- Скрипт проверки настройки
- Безопасность и best practices
- FAQ (часто задаваемые вопросы)
- Устранение проблем

**Когда использовать:**
- Нужны все детали настройки
- Возникли проблемы
- Настройка для продакшена
- Хотите понять как всё работает

---

## 🛠️ Вспомогательные инструменты

### 1. Скрипт проверки настройки

**Файл:** `test_gigachat.py`

**Назначение:** Проверяет все аспекты настройки GigaChat API

**Использование:**
```powershell
python test_gigachat.py
```

**Что проверяет:**
- ✓ Переменная окружения `GIGACHAT_AUTH_KEY`
- ✓ Конфигурация в `config.yaml`
- ✓ Установка GigaChat SDK
- ✓ Подключение к API (опционально)

**Результат:**
```
============================================================
[SUCCESS] Все обязательные проверки пройдены!
============================================================
```

### 2. Скрипт автоматической настройки

**Файл:** `setup_gigachat.ps1`

**Назначение:** Автоматизирует процесс настройки GigaChat API

**Использование:**
```powershell
.\setup_gigachat.ps1
```

**Что делает:**
1. Запрашивает и устанавливает Authorization Key
2. Создаёт/обновляет config.yaml из шаблона
3. Проверяет и устанавливает GigaChat SDK
4. Запускает проверку настройки

**Преимущества:**
- Интерактивный режим с подсказками
- Проверка формата ключа
- Создание бэкапов
- Автоматическая установка SDK

### 3. Шаблон конфигурации

**Файл:** `config.gigachat.yaml.example`

**Назначение:** Готовый к использованию шаблон config.yaml с параметрами GigaChat

**Использование:**
```powershell
# Скопировать в config.yaml
copy config.gigachat.yaml.example config.yaml

# Или использовать setup_gigachat.ps1
.\setup_gigachat.ps1
```

**Содержимое:**
- Полная конфигурация GigaChat с комментариями
- Параметры CPG
- Настройки векторного хранилища
- Конфигурация RAG
- Настройки логирования

---

## 📋 Ваши параметры GigaChat

Для вашего удобства все параметры указаны в документации:

```yaml
# Ваши данные
Client ID: 019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6
Scope:     GIGACHAT_API_PERS
Model:     GigaChat-2-Pro

# Устанавливается отдельно
Auth Key:  [в переменной окружения GIGACHAT_AUTH_KEY]
```

**Важно:**
- Authorization Key хранится в переменной окружения (безопасность)
- Остальные параметры в `config.yaml` (можно в Git)
- Client ID, Scope, Model уже настроены во всех примерах

---

## 🎯 Рекомендуемый путь изучения

### Для начинающих:

1. **Начните с Быстрого старта**
   - Откройте: [GIGACHAT_QUICKSTART.md](../GIGACHAT_QUICKSTART.md)
   - Следуйте 3 шагам
   - Запустите проверку

2. **При возникновении проблем**
   - Откройте: [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md)
   - Найдите раздел "Устранение проблем"
   - Запустите `test_gigachat.py` для диагностики

3. **Сохраните шпаргалку**
   - Откройте: [GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md)
   - Добавьте в закладки
   - Используйте для быстрой справки

### Для опытных пользователей:

1. **Используйте шпаргалку**
   - [GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md) - всё на одной странице

2. **Автоматическая настройка**
   ```powershell
   .\setup_gigachat.ps1
   ```

3. **Полная документация при необходимости**
   - [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md)

---

## 🔐 Безопасность

### Правильное хранение секретов

**✓ Правильно:**
```powershell
# В переменной окружения
$env:GIGACHAT_AUTH_KEY = "your_key"

# В файле .env (уже в .gitignore)
GIGACHAT_AUTH_KEY=your_key
```

**✗ Неправильно:**
```python
# НЕ ДЕЛАЙТЕ ТАК!
auth_key = "your_key"  # Попадёт в Git!
```

### Проверка .gitignore

Файл `.env` уже добавлен в `.gitignore`:
```gitignore
# .gitignore (уже есть)
.env
*.env
.env.*
```

**Убедитесь, что:**
- Authorization Key только в переменных окружения или .env
- .env файл в .gitignore
- Никогда не коммитьте секреты в Git

---

## ❓ Часто задаваемые вопросы

### Q: Какой документ открыть первым?

**A:** Зависит от опыта:
- **Новичок:** [GIGACHAT_QUICKSTART.md](../GIGACHAT_QUICKSTART.md)
- **Опытный:** [GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md)
- **Проблемы:** [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md) → "Устранение проблем"

### Q: Нужно ли устанавливать Client ID отдельно?

**A:** Нет! Client ID уже указан во всех примерах конфигурации:
```yaml
client_id: "019a7e2b-aeb3-78c4-ba3d-ddc1142b4ee6"
```

Вам нужно установить только `GIGACHAT_AUTH_KEY`.

### Q: Где взять Authorization Key?

**A:** Authorization Key выдаётся в личном кабинете GigaChat при регистрации приложения.

Формат: `Basic <base64_credentials>`

### Q: Как проверить, что всё работает?

**A:** Запустите скрипт проверки:
```powershell
python test_gigachat.py
```

Если все проверки пройдены - готово! ✓

### Q: Можно ли использовать автоматическую настройку?

**A:** Да! Рекомендуется:
```powershell
.\setup_gigachat.ps1
```

Скрипт проведёт через все шаги настройки.

---

## 📞 Поддержка

### При возникновении проблем:

1. **Запустить диагностику:**
   ```powershell
   python test_gigachat.py
   ```

2. **Проверить документацию:**
   - [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md) → "Устранение проблем"
   - [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md) → "FAQ"

3. **Проверить базовые вещи:**
   - Установлен ли ключ: `echo $env:GIGACHAT_AUTH_KEY`
   - Правильный ли формат (начинается с `Basic `)
   - Установлен ли SDK: `pip show gigachat`

4. **Официальная документация:**
   - https://developers.sber.ru/docs/ru/gigachat/

---

## 📊 Карта документации

```
RAG-CPGQL/
│
├── GIGACHAT_CHEATSHEET.md          ← Шпаргалка (1 мин)
├── GIGACHAT_QUICKSTART.md          ← Быстрый старт (5 мин)
├── docs/
│   ├── GIGACHAT_SETUP.md           ← Полная инструкция (15 мин)
│   └── GIGACHAT_README.md          ← Этот файл (навигация)
│
├── test_gigachat.py                ← Проверка настройки
├── setup_gigachat.ps1              ← Автоматическая настройка
└── config.gigachat.yaml.example    ← Шаблон конфигурации
```

---

## ✅ Чеклист готовности

Перед началом работы убедитесь:

- [ ] Прочитали быстрый старт: [GIGACHAT_QUICKSTART.md](../GIGACHAT_QUICKSTART.md)
- [ ] Установили `GIGACHAT_AUTH_KEY`
- [ ] Настроили `config.yaml`
- [ ] Установили GigaChat SDK: `pip install gigachat`
- [ ] Запустили проверку: `python test_gigachat.py`
- [ ] Получили "[SUCCESS] Все проверки пройдены!"
- [ ] Сохранили шпаргалку в закладках: [GIGACHAT_CHEATSHEET.md](../GIGACHAT_CHEATSHEET.md)

---

## 🎉 Готово к использованию!

После выполнения всех шагов вы можете:

1. **Использовать GigaChat в коде:**
   ```python
   from gigachat import GigaChat
   import os

   client = GigaChat(
       credentials=os.getenv("GIGACHAT_AUTH_KEY"),
       scope="GIGACHAT_API_PERS"
   )
   ```

2. **Интегрировать с RAG-CPGQL:**
   - Все агенты автоматически адаптируются к GigaChat
   - Работает с PostgreSQL, Linux Kernel, LLVM, Generic CPG
   - Поддержка мультидоменных запросов

3. **Масштабировать:**
   - Добавить новые модели в config.yaml
   - Настроить параметры (temperature, max_tokens)
   - Оптимизировать под ваши задачи

---

**Успешной работы с GigaChat API!** 🚀

Для вопросов см. [GIGACHAT_SETUP.md](GIGACHAT_SETUP.md) → раздел "Поддержка"
