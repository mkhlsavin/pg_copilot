# Руководство по устранению неполадок

Распространённые проблемы и их решения для CodeGraph.

## Содержание

- [Проблемы установки](#проблемы-установки)
- [CUDA не найдена](#cuda-не-найдена)
- [Не удалось подключиться к DuckDB](#не-удалось-подключиться-к-duckdb)
- [Не удалось инициализировать ChromaDB](#не-удалось-инициализировать-chromadb)
- [Ошибки импорта](#ошибки-импорта)
- [Проблемы с поставщиком LLM](#проблемы-с-поставщиком-llm)
- [Ошибка аутентификации GigaChat](#ошибка-аутентификации-gigachat)
- [Недостаточно памяти у локальной модели LLM](#недостаточно-памяти-у-локальной-модели-llm)
- [Таймаут ответа LLM](#таймаут-ответа-llm)
- [Проблемы с запросами](#проблемы-с-запросами)
- [Результаты не найдены](#результаты-не-найдены)
- [Медленная работа запросов](#медленная-работа-запросов)
- [Некорректные результаты](#некорректные-результаты)
- [Проблемы с сервером Joern](#проблемы-с-сервером-joern)
- [Сервер не запускается](#сервер-не-запускается)
- [Таймаут запроса CPGQL](#таймаут-запроса-cpgql)
- [Проблемы с памятью](#проблемы-с-памятью)
- [Недостаточно памяти во время обработки](#недостаточно-памяти-во-время-обработки)
- [Высокое использование памяти](#высокое-использование-памяти)
- [Отладка](#отладка)
- [Включение отладочного логирования](#включение-отладочного-логирования)
- [Проверка состояния компонентов](#проверка-состояния-компонентов)
- [Генерация отчёта об отладке](#генерация-отчёта-об-отладке)
- [Получение помощи](#получение-помощи)
- [Дальнейшие шаги](#дальнейшие-шаги)

## Проблемы установки

### CUDA не найдена

**Симптом:**

```
RuntimeError: CUDA not available
```

**Решение:**

```
# Проверка установки CUDA
nvidia-smi
nvcc --version

# Переустановка PyTorch с поддержкой CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Не удалось подключиться к DuckDB

**Симптом:**

```
duckdb.IOException: Could not open file 'cpg.duckdb'
```

**Решение:**

```
# Проверка существования файла
ls -la cpg.duckdb

# Проверка прав доступа
chmod 644 cpg.duckdb

# Проверка, не заблокирован ли файл другим процессом
lsof cpg.duckdb  # Linux/Mac
```

### Не удалось инициализировать ChromaDB

**Симптом:**

```
chromadb.errors.ChromaDBError: Collection not found
```

**Решение:**

```
# Проверка существования chromadb_storage
ls -la chromadb_storage/

# Повторная инициализация при необходимости
python scripts/init_vector_store.py
```

### Ошибки импорта

**Симптом:**

```
ModuleNotFoundError: No module named 'src'
```

**Решение:**

```
# Убедитесь, что вы находитесь в корне проекта
cd /путь/к/codegraph

# Добавьте в PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Или установите в режиме разработки
pip install -e .
```

## Проблемы с поставщиком LLM

### Ошибка аутентификации GigaChat

**Симптом:**

```
401 Unauthorized: Invalid credentials
```

**Решение:**

```
# Проверка переменной окружения
echo $GIGACHAT_AUTH_KEY

# Установите, если отсутствует
export GIGACHAT_AUTH_KEY="ваш_ключ"

# Проверка в Python
python -c "import os; print(os.environ.get('GIGACHAT_AUTH_KEY', 'НЕ УСТАНОВЛЕН'))"
```

### Недостаточно памяти у локальной модели LLM

**Симптом:**

```
CUDA out of memory
```

**Решение:**

```
# Уменьшите количество слоёв в config.yaml
llm:
  n_gpu_layers: 20  # Уменьшить с -1
  n_ctx: 4096       # Уменьшить размер контекста
```

Или используйте модель с меньшей квантованием:

```
# Используйте Q4_K_M вместо Q5_K_M
```

### Таймаут ответа LLM

**Симптом:**

```
TimeoutError: LLM did not respond within timeout
```

**Решение:**

```
# Увеличьте таймаут в config.yaml
llm:
  timeout: 120  # секунд
  max_retries: 3
```

## Проблемы с запросами

### Результаты не найдены

**Симптом:**

```
No methods found matching query
```

**Решения:**
1. **Проверьте орфографию** — имена методов чувствительны к регистру
2. **Используйте частичное совпадение** — попробуйте `*Transaction*` вместо `CommitTransaction`
3. **Проверьте базу данных** — убедитесь, что данные существуют:

```
sql
   SELECT COUNT(*) FROM nodes_method WHERE full_name LIKE '%Transaction%';
```

### Медленная работа запросов

**Симптом:**
Запрос выполняется более 10 секунд

**Решения:**

```
# Уменьшите объём поиска в config.yaml
retrieval:
  top_k_qa: 3      # Уменьшить с 10
  top_k_cpgql: 3   # Уменьшить с 10

# Отключите гибридный режим для ускорения
retrieval:
  hybrid:
    enabled: false
```

### Некорректные результаты

**Симптом:**
Ответы не соответствуют ожидаемым

**Решения:**
1. **Уточните вопрос** — будьте более конкретны
2. **Проверьте домен** — убедитесь, что выбран правильный домен
3. **Проверьте эмбеддинги** — пересоздайте, если повреждены:

```
bash
   python src/cpg_export/add_vector_embeddings.py --force
```

## Проблемы с сервером Joern

### Сервер не запускается

**Симптом:**

```
Connection refused on port 8080
```

**Решение:**

```
# Проверка, используется ли порт
netstat -ano | findstr :8080

# Завершите процесс, если необходимо
taskkill /F /PID <pid>

# Перезапустите Joern
powershell -ExecutionPolicy Bypass -File scripts/bootstrap_joern.ps1
```

### Таймаут запроса CPGQL

**Симптом:**

```
Joern query timed out
```

**Решение:**

```
# Увеличьте таймаут в config.yaml
joern:
  timeout: 60  # секунд

# Или используйте SQL-путь
cpg:
  prefer_sql: true
```

## Проблемы с памятью

### Недостаточно памяти во время обработки

**Симптом:**

```
MemoryError: Unable to allocate
```

**Решения:**

```
# Уменьшите размер пакетов
retrieval:
  batch_size: 25  # Уменьшить с 100

# Включите пошаговую обработку
processing:
  streaming: true
  chunk_size: 1000
```

### Высокое использование памяти

**Симптом:**
Система становится неотзывчивой

**Решения:**

```
# Мониторинг использования памяти
watch -n 1 'free -h'

# Очистка кэшей
python -c "from src.optimization.query_cache import QueryCache; QueryCache().clear()"

# Уменьшите использование памяти векторным хранилищем
# Используйте ChromaDB с хранением на диске
```

## Отладка

### Включение отладочного логирования

```
# В config.yaml
logging:
  level: DEBUG
```

Или через переменную окружения:

```
export LOG_LEVEL=DEBUG
python examples/demo_simple.py
```

### Проверка состояния компонентов

```
# Диагностический скрипт
from src.services.cpg_query_service import CPGQueryService
from src.retrieval.vector_store_real import VectorStoreReal

# Проверка DuckDB
cpg = CPGQueryService()
print(f"Methods: {cpg.count_methods()}")

# Проверка векторного хранилища
vs = VectorStoreReal()
print(f"QA docs: {vs.qa_collection.count()}")

# Проверка LLM
from src.llm.llm_interface_compat import get_llm
llm = get_llm()
print(f"LLM: {type(llm).__name__}")
```

### Генерация отчёта об отладке

```
python -c "
import sys
import platform

print('=== Информация о системе ===')
print(f'Python: {sys.version}')
print(f'Платформа: {platform.platform()}')

print('\n=== CUDA ===')
try:
    import torch
    print(f'PyTorch: {torch.__version__}')
    print(f'CUDA доступна: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'Версия CUDA: {torch.version.cuda}')
        print(f'GPU: {torch.cuda.get_device_name(0)}')
except ImportError:
    print('PyTorch не установлен')

print('\n=== Зависимости ===')
import duckdb
print(f'DuckDB: {duckdb.__version__}')

import chromadb
print(f'ChromaDB: {chromadb.__version__}')
"
```

## Получение помощи

Если проблемы сохраняются:

1. **Проверьте логи** в `logs/codegraph.log`
2. **Изучите существующие обращения** в репозитории
3. **Создайте новое обращение**, указав:
   - Сообщение об ошибке
   - Шаги для воспроизведения
   - Вывод отладочного отчёта
   - config.yaml (без конфиденциальных данных)

## Дальнейшие шаги

- [Установка](../getting-started/INSTALLATION.md) — руководство по настройке
- [Конфигурация](../getting-started/CONFIGURATION.md) — параметры конфигурации
- [Руководство пользователя TUI](TUI_USER_GUIDE.md) — инструкции по использованию
