# Отчёт по безопасности: FSIN Module

**Путь к проекту:** `C:\Users\user\Downloads\fsin_module`
**Время аудита:** 2025-12-09 20:43:19
**Длительность:** 0.02 секунд
**Проанализировано файлов:** 88

## Краткое резюме

| Серьёзность | Количество |
|----------|-------|
| 🔴 КРИТИЧЕСКИЙ | 2 |
| 🟠 ВЫСОКИЙ | 6 |
| 🟡 СРЕДНИЙ | 2 |
| 🟢 НИЗКИЙ | 0 |
| 🔵 ИНФОРМАЦИЯ | 0 |
| **ВСЕГО** | **10** |

> **КРИТИЧЕСКИЙ РИСК: В проекте обнаружены критические уязвимости, требующие немедленного исправления!**

## Соответствие D3FEND Source Code Hardening

| Техника | Название техники | Найдено | Статус | Применимость |
|---------|----------|---------|--------|---------------|
| D3-VI | Инициализация переменных | - | N/A | Только C/C++ (не применимо для Python) |
| D3-CS | Очистка учётных данных | 0 | ✅ | Применимо для Python |
| D3-IRV | Валидация диапазонов целых чисел | - | N/A | Только C/C++ (не применимо для Python) |
| D3-PV | Валидация указателей | - | N/A | Только C/C++ (не применимо для Python) |
| D3-RN | Обнуление ссылок | - | N/A | Только C/C++ (не применимо для Python) |
| D3-TL | Использование доверенных библиотек | - | N/A | Только C/C++ (не применимо для Python) |
| D3-VTV | Валидация типов переменных | - | N/A | Только C/C++ (не применимо для Python) |
| D3-MBSV | Валидация границ блоков памяти | - | N/A | Только C/C++ (не применимо для Python) |
| D3-NPC | Проверка NULL-указателей | - | N/A | Только C/C++ (не применимо для Python) |
| D3-DLV | Валидация доменной логики | 0 | ✅ | Применимо для Python |
| D3-OLV | Валидация операционной логики | 0 | ✅ | Применимо для Python |

**Общий показатель соответствия:** 100% (3/3 применимых техник)

## 🔴 КРИТИЧЕСКИЙ Уязвимости уровня (2)

### 1. SECRET_KEY with Fallback (File Scan)

**ID паттерна:** `FILE_SECRET_FALLBACK_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:25`
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html)

**Описание:** SECRET_KEY с небезопасным fallback-значением

**Уязвимый код:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'wekgh2o35b24uk5g23yuf23yu5g23tb2j4bt')
```

**Рекомендация:**
Удалите fallback-значение: SECRET_KEY = os.environ["SECRET_KEY"]

---

### 2. DEBUG=True (File Scan)

**ID паттерна:** `FILE_DJANGO_DEBUG_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:28`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html)

**Описание:** Django DEBUG режим включён по умолчанию

**Уязвимый код:**
```python
DEBUG = os.environ.get('DEBUG', True)
```

**Рекомендация:**
Установите DEBUG=False в production, используйте env var без True по умолчанию

---

## 🟠 ВЫСОКИЙ Уязвимости уровня (6)

### 1. Debug Permission (File Scan)

**ID паттерна:** `FILE_DEBUG_PERM_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\permissions.py:11`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html), [CWE-306](https://cwe.mitre.org/data/definitions/306.html)

**Описание:** Проверка разрешений на основе DEBUG

**Уязвимый код:**
```python
return settings.DEBUG
```

**Рекомендация:**
Никогда не используйте DEBUG в проверках разрешений, используйте RBAC

---

### 2. CORS Allow All (File Scan)

**ID паттерна:** `FILE_CORS_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:30`
**CWE:** [CWE-346](https://cwe.mitre.org/data/definitions/346.html)

**Описание:** CORS настроен на разрешение всех origin

**Уязвимый код:**
```python
CORS_ALLOW_ALL_ORIGINS = True
```

**Рекомендация:**
Установите CORS_ALLOW_ALL_ORIGINS=False, используйте CORS_ALLOWED_ORIGINS

---

### 3. ALLOWED_HOSTS Wildcard (File Scan)

**ID паттерна:** `FILE_HOSTS_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:32`
**CWE:** [CWE-942](https://cwe.mitre.org/data/definitions/942.html)

**Описание:** ALLOWED_HOSTS содержит wildcard

**Уязвимый код:**
```python
ALLOWED_HOSTS = json.loads(os.environ.get('ALLOWED_HOSTS', '["*"]'))
```

**Рекомендация:**
Укажите явные имена хостов в ALLOWED_HOSTS

---

### 4. Default DB Password (File Scan)

**ID паттерна:** `FILE_DB_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:113`
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html)

**Описание:** Пароль БД по умолчанию в настройках

**Уязвимый код:**
```python
'PASSWORD': os.environ.get('POSTGRES_PASS', default='postgres'),
```

**Рекомендация:**
Удалите fallback для пароля БД, требуйте DB_PASSWORD через env var

---

### 5. JWT Long Expiry (File Scan)

**ID паттерна:** `FILE_JWT_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:184`
**CWE:** [CWE-613](https://cwe.mitre.org/data/definitions/613.html)

**Описание:** Слишком долгое время жизни JWT access token (дни/недели)

**Уязвимый код:**
```python
"ACCESS_TOKEN_LIFETIME": timedelta(days=7),
```

**Рекомендация:**
Установите ACCESS_TOKEN_LIFETIME в минутах, используйте refresh tokens

---

### 6. Path Traversal (File Scan)

**ID паттерна:** `FILE_PATH_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\person\views.py:174`
**CWE:** [CWE-22](https://cwe.mitre.org/data/definitions/22.html)

**Описание:** Файловая операция без валидации пути

**Уязвимый код:**
```python
os.remove(os.path.join(settings.MEDIA_ROOT, photo.name))
```

**Рекомендация:**
Валидируйте пути с помощью os.path.realpath() и проверяйте префикс

---

## 🟡 СРЕДНИЙ Уязвимости уровня (2)

### 1. Debug Toolbar (File Scan)

**ID паттерна:** `FILE_TOOLBAR_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:61`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html)

**Описание:** Django Debug Toolbar безусловно включён

**Уязвимый код:**
```python
'debug_toolbar',
```

**Рекомендация:**
Включайте debug_toolbar только когда DEBUG=True

---

### 2. Large PAGE_SIZE (File Scan)

**ID паттерна:** `FILE_PAGESIZE_001`
**Файл:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:176`
**CWE:** [CWE-400](https://cwe.mitre.org/data/definitions/400.html), [CWE-770](https://cwe.mitre.org/data/definitions/770.html)

**Описание:** Слишком большой PAGE_SIZE в REST_FRAMEWORK (риск DoS)

**Уязвимый код:**
```python
'PAGE_SIZE': 10000,
```

**Рекомендация:**
Установите PAGE_SIZE в разумное значение (10-100), добавьте MAX_PAGE_SIZE

---

## Рекомендации

### 1. Захардкоженные учётные данные (1 найденные уязвимости)

**Проблема:** Пароли или ключи API в исходном коде
**Решение:** Храните учётные данные в переменных окружения
**Приоритет:** Высокий
**Трудозатраты:** Средние


---

*Отчёт сгенерирован RAG-CPGQL Security Audit Pipeline*