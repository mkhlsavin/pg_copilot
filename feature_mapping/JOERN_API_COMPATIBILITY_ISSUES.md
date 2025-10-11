# Joern API Compatibility Issues - Feature Mapping

**Date:** 2025-10-09
**Status:** Blocked by API incompatibilities

---

## Summary

Проект `feature_mapping` написан для старой версии Joern API и не совместим с текущей версией Joern 2.x. Попытки адаптации столкнулись с несколькими критическими проблемами.

---

## Issues Identified

### 1. CLI API Changes

**Problem:** Команды изменились между версиями
- `clearCpg` → не существует в Joern 2.x
- `importCpg(path, project)` → создаёт копию CPG в workspace вместо ссылки
- `loadCpg(path)` → создаёт проект с суффиксом (pg17_full.cpg → pg17_full.cpg1)
- `open(project)` → требует чтобы проект уже был в workspace

**Impact:** Невозможно загрузить существующий CPG без создания копий

### 2. Location API Changes

**Problem:** API для получения location изменился
```scala
// Old API (не работает):
node.location.map(_.filename)
node.location.flatMap(_.lineNumber)

// New API (работает):
Option(node.location.filename)
Option(node.location.lineNumber).flatten
```

**Status:** ✅ Fixed in joern_client.py

### 3. Import Changes

**Problem:** Некоторые импорты больше не существуют
```scala
// Old (не работает):
import overflowdb.traversal._
import scala.Option

// New (работает):
import io.shiftleft.semanticcpg.language._
// Option уже доступен по умолчанию
```

**Status:** ✅ Fixed in joern_client.py

### 4. HTTP Server Limitations

**Problem:** Joern HTTP server не возвращает stdout от `println()`
- `POST /query` возвращает только `{success: true, uuid: "..."}`
- Нет способа получить вывод скрипта через HTTP API
- Нет способа получить результаты traversal

**Impact:** Невозможно использовать HTTP API для поиска кандидатов

---

## Attempted Solutions

### Attempt 1: Fix CLI import commands
**Status:** ❌ Failed
- `loadCpg()` создаёт копию с суффиксом
- `importCpg()` требует не существующий проект
- `open()` не находит проект

### Attempt 2: Use HTTP server
**Status:** ❌ Blocked
- HTTP API не возвращает stdout
- Невозможно получить результаты поиска кандидатов

### Attempt 3: Direct server communication via cpgqls_client
**Status:** ⏳ In progress
- Используем уже работающий cpgqls_client из RAG
- Прямые запросы через HTTP

---

## Recommended Approach

### Option A: Manual Feature Tagging (QUICK)

Создать простой скрипт с cpgqls_client для добавления Feature тегов вручную для ключевых фич:

```python
from cpgqls_client import CPGQLSClient

client = CPGQLSClient("localhost:8080")

# Пример: тегировать MERGE функции
query = '''
val mergeFiles = cpg.file.name(".*merge.*").l
mergeFiles.foreach(f => f.newTagNodePair("Feature", "MERGE").store)
run.commit
'''
result = client.execute(query)
```

**Pros:**
- Быстро (несколько минут)
- Использует уже работающую инфраструктуру
- Можно вручную контролировать качество маппинга

**Cons:**
- Ручная работа для каждой фичи
- Не автоматизировано для всех 394 фич

### Option B: Rewrite Feature Mapping (SLOW)

Полностью переписать `feature_mapping` для работы с cpgqls_client и HTTP API

**Pros:**
- Полная автоматизация
- Работает для всех 394 фич

**Cons:**
- Требует несколько часов работы
- Нужно переписать логику поиска кандидатов
- Нужно адаптировать scoring к новому API

### Option C: Use Joern CLI scripts directly (MEDIUM)

Использовать `joern --script` но без импорта CPG в скрипте (предполагаем CPG уже загружен)

**Status:** Не проверено

---

## Recommendation for User

**Для продакшена рекомендую Option A:**

1. Создать список из 10-20 ключевых PostgreSQL фич:
   - MERGE
   - Logical replication
   - JSONB data type
   - Parallel query
   - Partitioning
   - WAL improvements
   - Security features (SCRAM, SSL)
   - Performance features (JIT, parallel)
   - Extension API
   - Replication slots

2. Для каждой фичи написать простой CPGQL запрос с тегированием:
   ```scala
   // MERGE
   cpg.file.name(".*merge.*").newTagNodePair("Feature", "MERGE").store
   cpg.method.name(".*merge.*").newTagNodePair("Feature", "MERGE").store
   run.commit

   // Logical replication
   cpg.file.name(".*logical.*repl.*").newTagNodePair("Feature", "Logical replication").store
   run.commit
   ```

3. Обновить RAG промпты для использования Feature тегов

4. Протестировать RAG с Feature-based запросами

**Время:** 1-2 часа вместо 5-8 часов на полную переработку

---

## Files Modified

1. ✅ `feature_mapping/joern_client.py` - Fixed location API
2. ✅ `feature_mapping/joern_http_client.py` - Created HTTP client (blocked)
3. ⏳ Need: Simple tagging script using cpgqls_client

---

## Next Steps

1. Создать `add_feature_tags.py` с cpgqls_client
2. Добавить теги для 10-20 ключевых фич
3. Обновить `rag_cpgql/src/generation/prompts.py` с Feature tag examples
4. Протестировать RAG запросы с Feature тегами
5. Документировать результаты

---

## Conclusion

Полная интеграция `feature_mapping` требует существенной переработки из-за несовместимости API.

Для продакшена достаточно ручного тегирования 10-20 ключевых фич, что займёт 1-2 часа вместо полной переработки (5-8 часов).

После ручного тегирования можно оценить эффективность Feature тегов в RAG и решить, стоит ли инвестировать время в полную автоматизацию.
