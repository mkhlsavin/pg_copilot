# План расширения обогащающих скриптов (ноябрь 2025)

## 1. Аудит фактических тегов
- Добавить утилиту `audit_missing_tags.py`, которая:
  - Сравнивает список `tag_categories` из `data/cpg_actual_tags.json` с фактическими тегами в CPG (`cpg.tag.nameExact("<tag>").count`).
  - Формирует отчёт с отсутствующими категориями и сохраняет его в `results/missing_tags_{timestamp}.json`.
- Подключить аудит к `enrich_cpg.ps1` через новый параметр `-AuditMissingTags` (по умолчанию выключено).

## 2. Новые и обновлённые скрипты обогащения
### 2.1 `enrich_concurrency_flags.sc` (новый)
- Источники данных: вызовы `LockAcquire*`, `LWLock*`, структуры `LOCKTAG`, `LWLock`, поля с суффиксами `_lock`, `_mutex`.
- Действия: помечать идентификаторы/поля тегом `is-lock`, фиксировать supporting-evidence (имя функции, файл, смещение).
- Типы узлов: LOCAL, IDENTIFIER, MEMBER.

### 2.2 `enrich_security_sensitivity.sc` (новый)
- Источники: параметры и локальные переменные, связанные с модулями `libpq`, `md5`, `pg_hba`, `ssl`, а также строковые литералы с ключевыми словами `password`, `secret`, `token`.
- Теги: `security-sensitivity = credential | auth-token | secret | personal-data`.
- Дополнительно анализировать функции `ClientAuthentication`, `CheckPasswordAuth`, `FunctionCallPrepare`, точки записи в каталоги пользователей.

### 2.3 Обновление `enrich_literal_semantics.sc`
- Расширить существующий скрипт, чтобы кроме `literal-kind` и `is-null-constant` добавлялись:
  - `literal-domain` — на основании контекста (wal, buffer, lock, error, catalog, transaction, visibility и т.д.).
  - `literal-severity` — по классам ошибок (`ERRCODE_*`, `PANIC`, `WARNING`, `LOG`).
  - `literal-constant` — запоминать исходное имя макроса/константы.
  - `is-bitmask` — определять по участию в операциях `|`, `&`, `<<` или по суффиксу `_MASK`.
  - `is-lock-constant` — распознавать значения `LOCKTAG_*`, `LOCKMODE`, `LWLockId`.
- Добавить таблицу соответствий в `schema/literal_domains.json`.

### 2.4 Интеграция в пайплайн
- Включить новые скрипты в профили `standard` и `full` (`enrich_cpg.ps1` и `enrich_cpg.sh`).
- Обновить `enrich_literal_semantics.sc` в общем списке Category 4.

## 3. Обновление экспорта и данных
- Обновить `export_tags.sc`, чтобы выгружать новые категории и значения.
- После выполнения `enrich_cpg.ps1 full`:
  - Перегенерировать `data/cpg_actual_tags.json`.
  - Обновить `data/enrichment_quality.json` через `verify_tag_coverage.py --output data/enrichment_quality.json`.
- Спланировать ночной прогон для пересборки ChromaDB (если добавляются новые коллекции).

## 4. Валидация
- Добавить скрипты-валидаторы:
  - `tests/test_literal_enrichment.sc` — проверяет наличие тегов на известных константах (`ERRCODE_*`, `LOCKTAG_*`).
  - `tests/test_concurrency_flags.sc` — проверяет `is-lock` на `ProcArrayLock`, `ProcGlobal->lock`, `LWLockArray`.
- Дополнительно подготовить python-тест `tests/test_security_sensitivity.py`, который сравнит количество тегов с ожидаемым порогом (например, ≥ 200 меток).

## 5. Документация и план
- Обновить `cpg_enrichment/README.md` (разделы «Variables & Identifiers», «Literals & Constants», «Security»).
- Зафиксировать новые показатели покрытия в `IMPLEMENTATION_PLAN.md` (Category 2 и Category 4).
- Подготовить заметку для основной документации (`README.md` в корне проекта) о появлении тегов `control-reason`, `is-lock`, `literal-domain` и др.

## 6. Следующие шаги
- После внедрения — полный прогон тестов `test_category1_integration.py` … `test_category7_integration.py` + новый `test_category8_integration.py`.
- Запустить `experiments/test_comprehensive_ragas.py`, чтобы измерить влияние новых тегов на генерацию запросов и ответы.
