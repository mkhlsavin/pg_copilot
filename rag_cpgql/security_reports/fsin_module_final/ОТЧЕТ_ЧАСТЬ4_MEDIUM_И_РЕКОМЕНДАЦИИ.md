# ОТЧЕТ АУДИТА - ЧАСТЬ 4: MEDIUM И РЕКОМЕНДАЦИИ

## MEDIUM уязвимости

### 1. Debug Toolbar

**Файл:** backend/settings.py:61

```python
'debug_toolbar',  # Всегда включен
```

**Исправление:**
```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
```

### 2. PAGE_SIZE 10000

**Файл:** backend/settings.py:176

```python
'PAGE_SIZE': 10000  # DoS риск
```

**Исправление:**
```python
'PAGE_SIZE': 20,
'MAX_PAGE_SIZE': 100,
```

---

## Приоритеты исправлений

### Немедленно (P1):
1. SECRET_KEY - убрать fallback
2. DEBUG - default=False

### Срочно (P2):
3. permissions.py - убрать DEBUG check
4. CORS - ограничить origins
5. ALLOWED_HOSTS - убрать wildcard
6. DB Password - убрать default
7. JWT - уменьшить lifetime
8. Path Traversal - валидация

### При релизе (P3):
9. Debug Toolbar - условно включать
10. PAGE_SIZE - уменьшить

---

## CPG Статистика

| Метрика | Значение |
|---------|----------|
| Методов | 1,309 |
| Вызовов | 12,788 |
| AST узлов | 52,280 |
| Quality | 86.2% |

---

*Отчет: RAG-CPGQL Security Audit*
*Дата: 2025-12-09*
