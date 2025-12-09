# Отчёт по безопасности: FSIN Module

**Путь к проекту:** `C:/Users/user/Downloads/fsin_module`
**Время аудита:** 2025-12-09 19:00:05
**Длительность:** 0.05 секунд
**Проанализировано файлов:** 88

## Краткое резюме

| Серьёзность | Количество |
|----------|-------|
| 🔴 КРИТИЧЕСКИЙ | 2 |
| 🟠 ВЫСОКИЙ | 6 |
| 🟡 СРЕДНИЙ | 3 |
| 🟢 НИЗКИЙ | 0 |
| 🔵 ИНФОРМАЦИЯ | 0 |
| **ВСЕГО** | **11** |

> **КРИТИЧЕСКИЙ РИСК: В проекте обнаружены критические уязвимости, требующие немедленного исправления!**

## Соответствие D3FEND Source Code Hardening

| Техника | Название техники | Найдено | Статус | Применимость |
|---------|----------|---------|--------|---------------|
| D3-VI | Инициализация переменных | - | N/A | Только C/C++ (не применимо для Python) |
| D3-CS | Очистка учётных данных | 4 | ⚠️ | Применимо для Python |
| D3-IRV | Валидация диапазонов целых чисел | - | N/A | Только C/C++ (не применимо для Python) |
| D3-PV | Валидация указателей | - | N/A | Только C/C++ (не применимо для Python) |
| D3-RN | Обнуление ссылок | - | N/A | Только C/C++ (не применимо для Python) |
| D3-TL | Использование доверенных библиотек | - | N/A | Только C/C++ (не применимо для Python) |
| D3-VTV | Валидация типов переменных | - | N/A | Только C/C++ (не применимо для Python) |
| D3-MBSV | Валидация границ блоков памяти | - | N/A | Только C/C++ (не применимо для Python) |
| D3-NPC | Проверка NULL-указателей | - | N/A | Только C/C++ (не применимо для Python) |
| D3-DLV | Валидация доменной логики | 0 | ✅ | Применимо для Python |
| D3-OLV | Валидация операционной логики | 0 | ✅ | Применимо для Python |

**Общий показатель соответствия:** 67% (2/3 применимых техник)

### Детали найденных учётных данных (D3-CS)

**1. unknown:15**
   ```python
   """
        Create and save a user with the given username, email, and password.
        """
   ```
   remediation: Никогда не храните учётные данные в исходном коде:
- Используйте переменные окружения: os.environ["SECRET_KEY"]
- Используйте файлы конфигурации (не в VCS)
- Используйте сервисы управления секретами (Vault, AWS Secrets Manager)

**2. unknown:25**
   ```python
   'SECRET_KEY'
   ```
   remediation: Никогда не храните учётные данные в исходном коде:
- Используйте переменные окружения: os.environ["SECRET_KEY"]
- Используйте файлы конфигурации (не в VCS)
- Используйте сервисы управления секретами (Vault, AWS Secrets Manager)

**3. unknown:10**
   ```python
   '--password'
   ```
   remediation: Никогда не храните учётные данные в исходном коде:
- Используйте переменные окружения: os.environ["SECRET_KEY"]
- Используйте файлы конфигурации (не в VCS)
- Используйте сервисы управления секретами (Vault, AWS Secrets Manager)

**4. unknown:10**
   ```python
   "Admin's password"
   ```
   remediation: Никогда не храните учётные данные в исходном коде:
- Используйте переменные окружения: os.environ["SECRET_KEY"]
- Используйте файлы конфигурации (не в VCS)
- Используйте сервисы управления секретами (Vault, AWS Secrets Manager)


## 🔴 КРИТИЧЕСКИЙ Уязвимости уровня (2)

### 1. SECRET_KEY with Fallback (File Scan)

**ID паттерна:** `FILE_SECRET_FALLBACK_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:25`
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html)

**Описание:** SECRET_KEY with insecure fallback value

**Уязвимый код:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'wekgh2o35b24uk5g23yuf23yu5g23tb2j4bt')
```

**remediation:**
Remove fallback: SECRET_KEY = os.environ['SECRET_KEY']

---

### 2. DEBUG=True (File Scan)

**ID паттерна:** `FILE_DJANGO_DEBUG_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:28`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html)

**Описание:** Django DEBUG mode enabled by default

**Уязвимый код:**
```python
DEBUG = os.environ.get('DEBUG', True)
```

**remediation:**
Set DEBUG=False in production, use env var without True default

---

## 🟠 ВЫСОКИЙ Уязвимости уровня (6)

### 1. Debug Permission (File Scan)

**ID паттерна:** `FILE_DEBUG_PERM_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\permissions.py:11`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html), [CWE-306](https://cwe.mitre.org/data/definitions/306.html)

**Описание:** Permission check based on DEBUG setting

**Уязвимый код:**
```python
return settings.DEBUG
```

**remediation:**
Never use DEBUG in permission checks, use proper RBAC

---

### 2. CORS Allow All (File Scan)

**ID паттерна:** `FILE_CORS_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:30`
**CWE:** [CWE-346](https://cwe.mitre.org/data/definitions/346.html)

**Описание:** CORS configured to allow all origins

**Уязвимый код:**
```python
CORS_ALLOW_ALL_ORIGINS = True
```

**remediation:**
Set CORS_ALLOW_ALL_ORIGINS=False, use CORS_ALLOWED_ORIGINS list

---

### 3. ALLOWED_HOSTS Wildcard (File Scan)

**ID паттерна:** `FILE_HOSTS_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:32`
**CWE:** [CWE-942](https://cwe.mitre.org/data/definitions/942.html)

**Описание:** ALLOWED_HOSTS contains wildcard

**Уязвимый код:**
```python
ALLOWED_HOSTS = json.loads(os.environ.get('ALLOWED_HOSTS', '["*"]'))
```

**remediation:**
Specify explicit hostnames in ALLOWED_HOSTS

---

### 4. Default DB Password (File Scan)

**ID паттерна:** `FILE_DB_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:113`
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html)

**Описание:** Default database password in settings

**Уязвимый код:**
```python
'PASSWORD': os.environ.get('POSTGRES_PASS', default='postgres'),
```

**remediation:**
Remove default password fallback, require DB_PASSWORD env var

---

### 5. JWT Long Expiry (File Scan)

**ID паттерна:** `FILE_JWT_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:184`
**CWE:** [CWE-613](https://cwe.mitre.org/data/definitions/613.html)

**Описание:** JWT access token lifetime too long (days/weeks)

**Уязвимый код:**
```python
"ACCESS_TOKEN_LIFETIME": timedelta(days=7),
```

**remediation:**
Set ACCESS_TOKEN_LIFETIME to minutes, use refresh tokens

---

### 6. Path Traversal (File Scan)

**ID паттерна:** `FILE_PATH_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\person\views.py:174`
**CWE:** [CWE-22](https://cwe.mitre.org/data/definitions/22.html)

**Описание:** File operation without path validation

**Уязвимый код:**
```python
os.remove(os.path.join(settings.MEDIA_ROOT, photo.name))
```

**remediation:**
Валидируйте пути с помощью os.path.realpath() и проверяйте префикс

---

## 🟡 СРЕДНИЙ Уязвимости уровня (3)

### 1. Debug Toolbar (File Scan)

**ID паттерна:** `FILE_TOOLBAR_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:61`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html)

**Описание:** Django Debug Toolbar unconditionally enabled

**Уязвимый код:**
```python
'debug_toolbar',
```

**remediation:**
Enable debug_toolbar only when DEBUG is True

---

### 2. Large PAGE_SIZE (File Scan)

**ID паттерна:** `FILE_PAGESIZE_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:176`
**CWE:** [CWE-400](https://cwe.mitre.org/data/definitions/400.html), [CWE-770](https://cwe.mitre.org/data/definitions/770.html)

**Описание:** REST_FRAMEWORK PAGE_SIZE too large (DoS risk)

**Уязвимый код:**
```python
'PAGE_SIZE': 10000,
```

**remediation:**
Set PAGE_SIZE to reasonable value (10-100), add MAX_PAGE_SIZE

---

### 3. Potential SQL Injection

**ID паттерна:** `DJANGO_SQL_INJECTION`
**Файл:** `unknown:426`
**CWE:** [CWE-89](https://cwe.mitre.org/data/definitions/89.html)

**Описание:** Database execute operation may be vulnerable to SQL injection if user input is concatenated

**Уязвимый код:**
```python
report.execute()
```

**remediation:**
Используйте параметризованные запросы или Django ORM вместо raw SQL

---

## Рекомендации

### 1. SQL-инъекция (1 найденные уязвимости)

**Проблема:** Возможность SQL-инъекции при конкатенации пользовательского ввода
**Решение:** Используйте параметризованные запросы вместо конкатенации строк
**Приоритет:** Высокий
**Трудозатраты:** Низкие

**Пример:**
```python
# Было:
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Стало:
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

### 2. Захардкоженные учётные данные (1 найденные уязвимости)

**Проблема:** Пароли или ключи API в исходном коде
**Решение:** Храните учётные данные в переменных окружения
**Приоритет:** Высокий
**Трудозатраты:** Средние


---

*Отчёт сгенерирован RAG-CPGQL Security Audit Pipeline*