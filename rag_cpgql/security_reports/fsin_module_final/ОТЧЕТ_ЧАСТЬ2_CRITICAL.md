# ОТЧЕТ АУДИТА - ЧАСТЬ 2: КРИТИЧЕСКИЕ УЯЗВИМОСТИ

## 1. SECRET_KEY с небезопасным fallback

**Файл:** backend/settings.py:25
**CWE-798:** Use of Hard-coded Credentials
**Severity:** 9.0/10

**Код:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'wekgh2o35b24uk5g23yuf23yu5g23tb2j4bt')
```

**Риски:**
- Подделка CSRF токенов
- Компрометация сессий
- Дешифровка подписанных cookies

**Исправление:**
```python
SECRET_KEY = os.environ['SECRET_KEY']  # Обязательная переменная
```

---

## 2. DEBUG=True по умолчанию

**Файл:** backend/settings.py:28
**CWE-489:** Active Debug Code
**Severity:** 9.0/10

**Код:**
```python
DEBUG = os.environ.get('DEBUG', True)
```

**Риски:**
- Раскрытие стек-трейсов
- Раскрытие SQL запросов
- Раскрытие env переменных

**Исправление:**
```python
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')
```
