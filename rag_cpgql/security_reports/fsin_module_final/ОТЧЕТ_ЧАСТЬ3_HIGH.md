# ОТЧЕТ АУДИТА - ЧАСТЬ 3: УЯЗВИМОСТИ HIGH

## 1. Permission Check на DEBUG

**Файл:** backend/permissions.py:11
**CWE:** 489, 306

```python
return settings.DEBUG  # ОПАСНО!
```

**Исправление:** Использовать RBAC:
```python
return request.user.has_perm('app.permission_name')
```

---

## 2. CORS Allow All

**Файл:** backend/settings.py:30
**CWE-346**

```python
CORS_ALLOW_ALL_ORIGINS = True
```

**Исправление:**
```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = ["https://your-domain.com"]
```

---

## 3. ALLOWED_HOSTS Wildcard

**Файл:** backend/settings.py:32
**CWE-942**

```python
ALLOWED_HOSTS = json.loads(os.environ.get('ALLOWED_HOSTS', '["*"]'))
```

**Исправление:** Убрать wildcard default.

---

## 4. Default DB Password

**Файл:** backend/settings.py:113
**CWE-798**

```python
'PASSWORD': os.environ.get('POSTGRES_PASS', default='postgres')
```

**Исправление:** Убрать default password.

---

## 5. JWT 7 дней

**Файл:** backend/settings.py:184
**CWE-613**

```python
"ACCESS_TOKEN_LIFETIME": timedelta(days=7)
```

**Исправление:**
```python
"ACCESS_TOKEN_LIFETIME": timedelta(minutes=15)
```

---

## 6. Path Traversal

**Файл:** person/views.py:174
**CWE-22**

```python
os.remove(os.path.join(settings.MEDIA_ROOT, photo.name))
```

**Исправление:** Валидировать путь через `os.path.realpath()`.
