# Security Audit Report: FSIN Module

**Project Path:** `C:/Users/user/Downloads/fsin_module`
**Audit Time:** 2025-12-09 19:00:05
**Duration:** 0.05 seconds
**Files Scanned:** 88

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 2 |
| 🟠 HIGH | 6 |
| 🟡 MEDIUM | 3 |
| 🟢 LOW | 0 |
| 🔵 INFO | 0 |
| **TOTAL** | **11** |

> **CRITICAL RISK: This project has critical security vulnerabilities that must be addressed immediately!**

## D3FEND Source Code Hardening Compliance

| Technique | Technique Name | Found | Status | Applicability |
|---------|----------|---------|--------|---------------|
| D3-VI | Variable Initialization | - | N/A | C/C++ only (not applicable for Python) |
| D3-CS | Credential Scrubbing | 4 | ⚠️ | Applicable for Python |
| D3-IRV | Integer Range Validation | - | N/A | C/C++ only (not applicable for Python) |
| D3-PV | Pointer Validation | - | N/A | C/C++ only (not applicable for Python) |
| D3-RN | Reference Nullification | - | N/A | C/C++ only (not applicable for Python) |
| D3-TL | Trusted Library | - | N/A | C/C++ only (not applicable for Python) |
| D3-VTV | Variable Type Validation | - | N/A | C/C++ only (not applicable for Python) |
| D3-MBSV | Memory Block Start Validation | - | N/A | C/C++ only (not applicable for Python) |
| D3-NPC | Null Pointer Checking | - | N/A | C/C++ only (not applicable for Python) |
| D3-DLV | Domain Logic Validation | 0 | ✅ | Applicable for Python |
| D3-OLV | Operational Logic Validation | 0 | ✅ | Applicable for Python |

**Overall Compliance Score:** 67% (2/3 applicable techniques)

### Credential Findings Details (D3-CS)

**1. unknown:15**
   ```python
   """
        Create and save a user with the given username, email, and password.
        """
   ```
   remediation: Use environment variables: os.environ.get("SECRET_KEY")

**2. unknown:25**
   ```python
   'SECRET_KEY'
   ```
   remediation: Use environment variables: os.environ.get("SECRET_KEY")

**3. unknown:10**
   ```python
   '--password'
   ```
   remediation: Use environment variables: os.environ.get("SECRET_KEY")

**4. unknown:10**
   ```python
   "Admin's password"
   ```
   remediation: Use environment variables: os.environ.get("SECRET_KEY")


## 🔴 CRITICAL Severity Findings (2)

### 1. SECRET_KEY with Fallback (File Scan)

**Pattern ID:** `FILE_SECRET_FALLBACK_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:25`
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html)

**Description:** SECRET_KEY with insecure fallback value

**Vulnerable Code:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'wekgh2o35b24uk5g23yuf23yu5g23tb2j4bt')
```

**remediation:**
Remove fallback: SECRET_KEY = os.environ['SECRET_KEY']

---

### 2. DEBUG=True (File Scan)

**Pattern ID:** `FILE_DJANGO_DEBUG_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:28`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html)

**Description:** Django DEBUG mode enabled by default

**Vulnerable Code:**
```python
DEBUG = os.environ.get('DEBUG', True)
```

**remediation:**
Set DEBUG=False in production, use env var without True default

---

## 🟠 HIGH Severity Findings (6)

### 1. Debug Permission (File Scan)

**Pattern ID:** `FILE_DEBUG_PERM_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\permissions.py:11`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html), [CWE-306](https://cwe.mitre.org/data/definitions/306.html)

**Description:** Permission check based on DEBUG setting

**Vulnerable Code:**
```python
return settings.DEBUG
```

**remediation:**
Never use DEBUG in permission checks, use proper RBAC

---

### 2. CORS Allow All (File Scan)

**Pattern ID:** `FILE_CORS_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:30`
**CWE:** [CWE-346](https://cwe.mitre.org/data/definitions/346.html)

**Description:** CORS configured to allow all origins

**Vulnerable Code:**
```python
CORS_ALLOW_ALL_ORIGINS = True
```

**remediation:**
Set CORS_ALLOW_ALL_ORIGINS=False, use CORS_ALLOWED_ORIGINS list

---

### 3. ALLOWED_HOSTS Wildcard (File Scan)

**Pattern ID:** `FILE_HOSTS_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:32`
**CWE:** [CWE-942](https://cwe.mitre.org/data/definitions/942.html)

**Description:** ALLOWED_HOSTS contains wildcard

**Vulnerable Code:**
```python
ALLOWED_HOSTS = json.loads(os.environ.get('ALLOWED_HOSTS', '["*"]'))
```

**remediation:**
Specify explicit hostnames in ALLOWED_HOSTS

---

### 4. Default DB Password (File Scan)

**Pattern ID:** `FILE_DB_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:113`
**CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html)

**Description:** Default database password in settings

**Vulnerable Code:**
```python
'PASSWORD': os.environ.get('POSTGRES_PASS', default='postgres'),
```

**remediation:**
Remove default password fallback, require DB_PASSWORD env var

---

### 5. JWT Long Expiry (File Scan)

**Pattern ID:** `FILE_JWT_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:184`
**CWE:** [CWE-613](https://cwe.mitre.org/data/definitions/613.html)

**Description:** JWT access token lifetime too long (days/weeks)

**Vulnerable Code:**
```python
"ACCESS_TOKEN_LIFETIME": timedelta(days=7),
```

**remediation:**
Set ACCESS_TOKEN_LIFETIME to minutes, use refresh tokens

---

### 6. Path Traversal (File Scan)

**Pattern ID:** `FILE_PATH_001`
**File:** `C:\Users\user\Downloads\fsin_module\person\views.py:174`
**CWE:** [CWE-22](https://cwe.mitre.org/data/definitions/22.html)

**Description:** File operation without path validation

**Vulnerable Code:**
```python
os.remove(os.path.join(settings.MEDIA_ROOT, photo.name))
```

**remediation:**
Validate paths with os.path.realpath() and check prefix

---

## 🟡 MEDIUM Severity Findings (3)

### 1. Debug Toolbar (File Scan)

**Pattern ID:** `FILE_TOOLBAR_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:61`
**CWE:** [CWE-489](https://cwe.mitre.org/data/definitions/489.html)

**Description:** Django Debug Toolbar unconditionally enabled

**Vulnerable Code:**
```python
'debug_toolbar',
```

**remediation:**
Enable debug_toolbar only when DEBUG is True

---

### 2. Large PAGE_SIZE (File Scan)

**Pattern ID:** `FILE_PAGESIZE_001`
**File:** `C:\Users\user\Downloads\fsin_module\backend\settings.py:176`
**CWE:** [CWE-400](https://cwe.mitre.org/data/definitions/400.html), [CWE-770](https://cwe.mitre.org/data/definitions/770.html)

**Description:** REST_FRAMEWORK PAGE_SIZE too large (DoS risk)

**Vulnerable Code:**
```python
'PAGE_SIZE': 10000,
```

**remediation:**
Set PAGE_SIZE to reasonable value (10-100), add MAX_PAGE_SIZE

---

### 3. Potential SQL Injection

**Pattern ID:** `DJANGO_SQL_INJECTION`
**File:** `unknown:426`
**CWE:** [CWE-89](https://cwe.mitre.org/data/definitions/89.html)

**Description:** Database execute operation may be vulnerable to SQL injection if user input is concatenated

**Vulnerable Code:**
```python
report.execute()
```

**remediation:**
Use parameterized queries or Django ORM instead of raw SQL

---

## Recommendations

### 1. SQL Injection (1 findings)

**Problem:** SQL Injection via user input concatenation
**Solution:** Use parameterized queries instead of string concatenation
**Priority:** High
**Effort:** Low

**Example:**
```python
# Before:
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# After:
cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

### 2. Hardcoded Credentials (1 findings)

**Problem:** Passwords or API keys in source code
**Solution:** Store credentials in environment variables
**Priority:** High
**Effort:** Medium


---

*Report generated by RAG-CPGQL Security Audit Pipeline*