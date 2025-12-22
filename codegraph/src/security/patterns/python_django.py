"""
Python/Django Security Pattern Library

This module contains security vulnerability patterns specific to Python and Django
applications. Patterns detect misconfigurations, hardcoded secrets, and common
Python security issues.

Supports both:
- File-based scanning (regex patterns for direct file analysis)
- CPG-based detection (CPGQL queries for Code Property Graph analysis)
"""

from typing import Dict, List, Any, Pattern
from dataclasses import dataclass
import re

from src.security._base import (
    VulnerabilitySeverity,
    VulnerabilityCategory,
    SecurityPattern,
)


# ============================================================================
# FILE-BASED PATTERNS (Regex for direct file scanning)
# ============================================================================

@dataclass
class FilePattern:
    """Pattern for direct file-based scanning without CPG."""
    id: str
    name: str
    category: VulnerabilityCategory
    severity: VulnerabilitySeverity
    description: str
    file_pattern: str  # Glob pattern for files to scan
    regex: Pattern  # Compiled regex pattern
    negative_regex: Pattern = None  # Pattern that should NOT match (safe pattern)
    cwe_ids: List[str] = None
    remediation: str = ""
    example_vulnerable: str = ""
    example_secure: str = ""


# ============================================================================
# CRITICAL SEVERITY - DJANGO PATTERNS
# ============================================================================

DJANGO_DEBUG_MODE = SecurityPattern(
    id="DJANGO_DEBUG_001",
    name="Django DEBUG Mode Enabled",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Django DEBUG=True exposes sensitive information including full tracebacks, "
        "settings, SQL queries, and template context. Must be False in production."
    ),
    cpgql_query="""
        -- Find DEBUG=True assignments in settings files
        SELECT DISTINCT
            'DJANGO_DEBUG_001' AS pattern_id,
            filename,
            line_number,
            code,
            'DEBUG mode enabled' AS finding,
            'CRITICAL' AS severity
        FROM nodes_assignment
        WHERE LOWER(filename) LIKE '%settings%'
          AND code LIKE '%DEBUG%'
          AND (code LIKE '%True%' OR code LIKE '%1%')
          AND code NOT LIKE '%environ%'
          AND code NOT LIKE '%getenv%'
        LIMIT 10;
    """,
    cwe_ids=["CWE-489", "CWE-215"],
    remediation=(
        "1. Set DEBUG=False in production settings\n"
        "2. Use environment variable: DEBUG=os.environ.get('DEBUG', 'False').lower() == 'true'\n"
        "3. Create separate settings files for dev/prod environments\n"
        "4. Never deploy with DEBUG=True"
    ),
    example_code="""
        # VULNERABLE
        DEBUG = True
        DEBUG = os.environ.get('DEBUG', True)  # True as default!

        # SECURE
        DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
        DEBUG = False  # Production setting
    """,
    test_cases=[
        {"name": "DEBUG=True literal", "code": "DEBUG = True", "expected": True},
        {"name": "DEBUG from env with True default", "code": "DEBUG = os.environ.get('DEBUG', True)", "expected": True},
        {"name": "DEBUG=False literal", "code": "DEBUG = False", "expected": False},
    ]
)

DJANGO_SECRET_KEY_HARDCODED = SecurityPattern(
    id="DJANGO_SECRET_001",
    name="Hardcoded Django SECRET_KEY",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Django SECRET_KEY is used for cryptographic signing and must be secret. "
        "Hardcoding it in source code exposes it in version control, leading to "
        "session hijacking, CSRF bypass, and data tampering."
    ),
    cpgql_query="""
        -- Find hardcoded SECRET_KEY in settings
        SELECT DISTINCT
            'DJANGO_SECRET_001' AS pattern_id,
            filename,
            line_number,
            CASE
                WHEN LENGTH(code) > 100 THEN SUBSTRING(code, 1, 100) || '...'
                ELSE code
            END AS code,
            'Hardcoded SECRET_KEY' AS finding,
            'CRITICAL' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%SECRET_KEY%=%'
          AND code LIKE '%''%'
          AND code NOT LIKE '%environ%'
          AND code NOT LIKE '%getenv%'
          AND code NOT LIKE '%config%'
        LIMIT 10;
    """,
    cwe_ids=["CWE-798", "CWE-321"],
    remediation=(
        "1. Generate a new random SECRET_KEY\n"
        "2. Store in environment variable: SECRET_KEY = os.environ.get('SECRET_KEY')\n"
        "3. Never commit SECRET_KEY to version control\n"
        "4. Use different keys for dev/staging/production"
    ),
    example_code="""
        # VULNERABLE
        SECRET_KEY = 'wekgh2o35b24uk5g23yuf23yu5g23tb2j4bt'
        SECRET_KEY = os.environ.get('SECRET_KEY', 'hardcoded-fallback-key')

        # SECURE
        SECRET_KEY = os.environ['SECRET_KEY']  # Fails if not set
        SECRET_KEY = os.environ.get('SECRET_KEY')  # No fallback
    """,
    test_cases=[
        {"name": "Hardcoded secret", "code": "SECRET_KEY = 'mysecret'", "expected": True},
        {"name": "From env only", "code": "SECRET_KEY = os.environ['SECRET_KEY']", "expected": False},
    ]
)

PYTHON_PICKLE_DESERIALIZATION = SecurityPattern(
    id="PYTHON_PICKLE_001",
    name="Unsafe Pickle Deserialization",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Deserializing pickle data from untrusted sources allows arbitrary code "
        "execution. Attackers can craft malicious pickle payloads to execute commands."
    ),
    cpgql_query="""
        -- Find pickle.load/loads calls
        SELECT DISTINCT
            'PYTHON_PICKLE_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Unsafe pickle deserialization' AS finding,
            'CRITICAL' AS severity
        FROM nodes_call
        WHERE name IN ('load', 'loads')
          AND (code LIKE '%pickle%' OR code LIKE '%cPickle%')
        LIMIT 20;
    """,
    cwe_ids=["CWE-502", "CWE-94"],
    remediation=(
        "1. Never unpickle untrusted data\n"
        "2. Use safe serialization: JSON, MessagePack, Protocol Buffers\n"
        "3. If pickle required, use hmac to verify data integrity\n"
        "4. Consider restricted unpickler with limited classes"
    ),
    example_code="""
        # VULNERABLE
        import pickle
        data = pickle.loads(user_input)  # RCE!

        # SECURE
        import json
        data = json.loads(user_input)  # Safe for untrusted data
    """,
    test_cases=[
        {"name": "pickle.loads", "code": "pickle.loads(data)", "expected": True},
        {"name": "json.loads", "code": "json.loads(data)", "expected": False},
    ]
)

PYTHON_EVAL_EXEC = SecurityPattern(
    id="PYTHON_EXEC_001",
    name="Code Execution via eval/exec",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Using eval() or exec() with user-controlled input allows arbitrary Python "
        "code execution. Attackers can run malicious code, access files, or execute system commands."
    ),
    cpgql_query="""
        -- Find eval/exec calls
        SELECT DISTINCT
            'PYTHON_EXEC_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Code execution via eval/exec' AS finding,
            'CRITICAL' AS severity
        FROM nodes_call
        WHERE name IN ('eval', 'exec', 'compile')
          AND filename NOT LIKE '%test%'
        LIMIT 20;
    """,
    cwe_ids=["CWE-94", "CWE-95"],
    remediation=(
        "1. Never use eval/exec with user input\n"
        "2. Use ast.literal_eval() for safe literal evaluation\n"
        "3. Implement proper parsers for DSLs\n"
        "4. Use sandboxed execution environments if needed"
    ),
    example_code="""
        # VULNERABLE
        result = eval(user_input)
        exec(f"x = {user_data}")

        # SECURE
        import ast
        result = ast.literal_eval(user_input)  # Only literals
    """,
    test_cases=[
        {"name": "eval call", "code": "eval(user_input)", "expected": True},
        {"name": "ast.literal_eval", "code": "ast.literal_eval(data)", "expected": False},
    ]
)

PYTHON_SQL_INJECTION = SecurityPattern(
    id="PYTHON_SQL_001",
    name="SQL Injection via Raw Queries",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL queries constructed through string formatting or concatenation with "
        "user input are vulnerable to SQL injection attacks."
    ),
    cpgql_query="""
        -- Find raw SQL execution
        SELECT DISTINCT
            'PYTHON_SQL_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Potential SQL injection' AS finding,
            'CRITICAL' AS severity
        FROM nodes_call
        WHERE name IN ('execute', 'raw', 'executemany')
          AND (code LIKE '%format%' OR code LIKE '%+%' OR code LIKE '%f"%' OR code LIKE "%f'%")
          AND filename NOT LIKE '%test%'
        LIMIT 20;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use Django ORM instead of raw SQL\n"
        "2. Use parameterized queries with placeholders\n"
        "3. cursor.execute('SELECT * FROM t WHERE id=%s', [user_id])\n"
        "4. Never use string formatting for SQL"
    ),
    example_code="""
        # VULNERABLE
        cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
        cursor.execute("SELECT * FROM users WHERE id=" + user_id)

        # SECURE
        cursor.execute("SELECT * FROM users WHERE id=%s", [user_id])
        User.objects.filter(id=user_id)  # Django ORM
    """,
    test_cases=[
        {"name": "f-string SQL", "code": 'cursor.execute(f"SELECT * FROM t WHERE id={id}")', "expected": True},
    ]
)


# ============================================================================
# HIGH SEVERITY - CONFIGURATION PATTERNS
# ============================================================================

DJANGO_CORS_ALL_ORIGINS = SecurityPattern(
    id="DJANGO_CORS_001",
    name="CORS Allows All Origins",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "CORS_ALLOW_ALL_ORIGINS=True allows any website to make authenticated "
        "requests to your API, enabling CSRF-like attacks and data theft."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_CORS_001' AS pattern_id,
            filename,
            line_number,
            code,
            'CORS allows all origins' AS finding,
            'HIGH' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%CORS_ALLOW_ALL_ORIGINS%'
          AND code LIKE '%True%'
        LIMIT 5;
    """,
    cwe_ids=["CWE-346", "CWE-942"],
    remediation=(
        "1. Set CORS_ALLOW_ALL_ORIGINS=False\n"
        "2. Define allowed origins explicitly:\n"
        "   CORS_ALLOWED_ORIGINS = ['https://trusted.example.com']\n"
        "3. Use CORS_ALLOWED_ORIGIN_REGEXES for patterns"
    ),
    example_code="""
        # VULNERABLE
        CORS_ALLOW_ALL_ORIGINS = True

        # SECURE
        CORS_ALLOW_ALL_ORIGINS = False
        CORS_ALLOWED_ORIGINS = [
            'https://frontend.example.com',
        ]
    """,
    test_cases=[]
)

DJANGO_ALLOWED_HOSTS_WILDCARD = SecurityPattern(
    id="DJANGO_HOSTS_001",
    name="ALLOWED_HOSTS Accepts Wildcard",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "ALLOWED_HOSTS=['*'] accepts requests from any hostname, enabling "
        "HTTP Host header attacks, cache poisoning, and phishing."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_HOSTS_001' AS pattern_id,
            filename,
            line_number,
            code,
            'ALLOWED_HOSTS accepts wildcard' AS finding,
            'HIGH' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%ALLOWED_HOSTS%'
          AND code LIKE '%*%'
        LIMIT 5;
    """,
    cwe_ids=["CWE-942", "CWE-20"],
    remediation=(
        "1. Specify exact hostnames: ALLOWED_HOSTS = ['example.com', 'www.example.com']\n"
        "2. Use environment variable for flexibility\n"
        "3. Never use ['*'] in production"
    ),
    example_code="""
        # VULNERABLE
        ALLOWED_HOSTS = ['*']
        ALLOWED_HOSTS = json.loads(os.environ.get('ALLOWED_HOSTS', '["*"]'))

        # SECURE
        ALLOWED_HOSTS = ['example.com', 'api.example.com']
        ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
    """,
    test_cases=[]
)

JWT_LONG_EXPIRY = SecurityPattern(
    id="JWT_EXPIRY_001",
    name="JWT Token Long Expiry",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "JWT access tokens with long expiry (>1 hour) increase the window for "
        "token theft and replay attacks. Recommended: 15-60 minutes for access tokens."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'JWT_EXPIRY_001' AS pattern_id,
            filename,
            line_number,
            code,
            'JWT long token expiry' AS finding,
            'HIGH' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%ACCESS_TOKEN_LIFETIME%'
          AND (code LIKE '%days%' OR code LIKE '%weeks%' OR code LIKE '%hours=24%')
        LIMIT 5;
    """,
    cwe_ids=["CWE-613"],
    remediation=(
        "1. Set ACCESS_TOKEN_LIFETIME to 15-60 minutes\n"
        "2. Use refresh tokens for longer sessions\n"
        "3. Implement token revocation\n"
        "   SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30)}"
    ),
    example_code="""
        # VULNERABLE
        SIMPLE_JWT = {
            'ACCESS_TOKEN_LIFETIME': timedelta(days=7),  # Too long!
        }

        # SECURE
        SIMPLE_JWT = {
            'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
            'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
        }
    """,
    test_cases=[]
)

PYTHON_PATH_TRAVERSAL = SecurityPattern(
    id="PYTHON_PATH_001",
    name="Path Traversal in File Operations",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "File paths constructed from user input without validation allow attackers "
        "to access or delete files outside intended directories using '../' sequences."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'PYTHON_PATH_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Potential path traversal' AS finding,
            'HIGH' AS severity
        FROM nodes_call
        WHERE name IN ('remove', 'unlink', 'rmdir', 'rmtree', 'open', 'rename')
          AND (code LIKE '%os.path.join%' OR code LIKE '%+%' OR code LIKE '%format%')
          AND code NOT LIKE '%realpath%'
          AND code NOT LIKE '%abspath%'
        LIMIT 20;
    """,
    cwe_ids=["CWE-22", "CWE-23"],
    remediation=(
        "1. Use os.path.realpath() to resolve the full path\n"
        "2. Verify resolved path starts with allowed base directory\n"
        "3. Reject paths containing '..' or starting with '/'\n"
        "4. Use Django's FileField for user uploads"
    ),
    example_code="""
        # VULNERABLE
        file_path = os.path.join(settings.MEDIA_ROOT, user_filename)
        os.remove(file_path)  # User can delete any file!

        # SECURE
        base_path = os.path.realpath(settings.MEDIA_ROOT)
        file_path = os.path.realpath(os.path.join(base_path, user_filename))
        if file_path.startswith(base_path):
            os.remove(file_path)
    """,
    test_cases=[]
)

DJANGO_CSRF_DISABLED = SecurityPattern(
    id="DJANGO_CSRF_001",
    name="CSRF Protection Disabled",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Disabling CSRF protection or using @csrf_exempt on views allows "
        "cross-site request forgery attacks where attackers trick users "
        "into performing unintended actions."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_CSRF_001' AS pattern_id,
            filename,
            line_number,
            code,
            'CSRF protection disabled' AS finding,
            'HIGH' AS severity
        FROM nodes_call
        WHERE name = 'csrf_exempt'
          OR code LIKE '%@csrf_exempt%'
        UNION
        SELECT DISTINCT
            'DJANGO_CSRF_001' AS pattern_id,
            filename,
            line_number,
            code,
            'CSRF middleware removed' AS finding,
            'HIGH' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%MIDDLEWARE%'
          AND code NOT LIKE '%CsrfViewMiddleware%'
        LIMIT 10;
    """,
    cwe_ids=["CWE-352"],
    remediation=(
        "1. Keep CsrfViewMiddleware in MIDDLEWARE\n"
        "2. Use @csrf_exempt only for true API endpoints with other auth\n"
        "3. Use {% csrf_token %} in forms\n"
        "4. For APIs, use JWT or token authentication instead"
    ),
    example_code="""
        # VULNERABLE
        @csrf_exempt
        def sensitive_view(request):
            # Unprotected!

        # SECURE
        def sensitive_view(request):
            # CSRF protected

        # API with proper auth
        @api_view(['POST'])
        @permission_classes([IsAuthenticated])
        def api_view(request):
            # JWT auth instead of CSRF
    """,
    test_cases=[]
)

PYTHON_SUBPROCESS_SHELL = SecurityPattern(
    id="PYTHON_SUBPROCESS_001",
    name="Subprocess with shell=True",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Using subprocess with shell=True and user input allows command injection. "
        "Attackers can execute arbitrary system commands through shell metacharacters."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'PYTHON_SUBPROCESS_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Subprocess shell=True' AS finding,
            'HIGH' AS severity
        FROM nodes_call
        WHERE name IN ('run', 'call', 'Popen', 'check_output', 'check_call')
          AND code LIKE '%shell%=%True%'
        LIMIT 20;
    """,
    cwe_ids=["CWE-78", "CWE-88"],
    remediation=(
        "1. Use shell=False (default) with argument list\n"
        "2. subprocess.run(['cmd', 'arg1', 'arg2'], shell=False)\n"
        "3. Use shlex.quote() if shell=True is unavoidable\n"
        "4. Consider subprocess.run with capture_output=True"
    ),
    example_code="""
        # VULNERABLE
        subprocess.run(f"ls {user_input}", shell=True)  # Command injection!

        # SECURE
        subprocess.run(["ls", user_input], shell=False)  # Safe
    """,
    test_cases=[]
)

DJANGO_DB_CREDENTIALS = SecurityPattern(
    id="DJANGO_DB_CREDS_001",
    name="Default Database Credentials",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Default or hardcoded database credentials (like postgres/postgres) "
        "in settings allow unauthorized database access if exposed."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_DB_CREDS_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Default database credentials' AS finding,
            'HIGH' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%DATABASES%'
          AND (code LIKE "%'PASSWORD'%'postgres'%"
               OR code LIKE "%'PASSWORD'%'admin'%"
               OR code LIKE "%'PASSWORD'%'root'%"
               OR code LIKE "%'PASSWORD'%'password'%")
        LIMIT 5;
    """,
    cwe_ids=["CWE-798", "CWE-259"],
    remediation=(
        "1. Use environment variables for all credentials\n"
        "2. DATABASES = {'default': {'PASSWORD': os.environ['DB_PASSWORD']}}\n"
        "3. Use secrets management (Vault, AWS Secrets Manager)\n"
        "4. Never use default credentials in any environment"
    ),
    example_code="""
        # VULNERABLE
        DATABASES = {
            'default': {
                'PASSWORD': os.environ.get('POSTGRES_PASS', 'postgres'),  # Default!
            }
        }

        # SECURE
        DATABASES = {
            'default': {
                'PASSWORD': os.environ['DB_PASSWORD'],  # Required, no fallback
            }
        }
    """,
    test_cases=[]
)


# ============================================================================
# MEDIUM SEVERITY PATTERNS
# ============================================================================

DJANGO_DEBUG_TOOLBAR = SecurityPattern(
    id="DJANGO_DEBUG_TOOLBAR_001",
    name="Debug Toolbar in Production",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Django Debug Toolbar exposes SQL queries, request data, settings, and "
        "internal state. Should only be enabled in development environments."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_DEBUG_TOOLBAR_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Debug toolbar may be in production' AS finding,
            'MEDIUM' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%debug_toolbar%'
          AND (code LIKE '%INSTALLED_APPS%' OR code LIKE '%MIDDLEWARE%')
          AND code NOT LIKE '%if DEBUG%'
          AND code NOT LIKE '%if settings.DEBUG%'
        LIMIT 5;
    """,
    cwe_ids=["CWE-489", "CWE-215"],
    remediation=(
        "1. Add debug toolbar conditionally:\n"
        "   if DEBUG: INSTALLED_APPS += ['debug_toolbar']\n"
        "2. Keep debug_toolbar only in dev settings\n"
        "3. Remove from requirements.txt in production"
    ),
    example_code="""
        # VULNERABLE
        INSTALLED_APPS = [
            'debug_toolbar',  # Always loaded!
            ...
        ]

        # SECURE
        if DEBUG:
            INSTALLED_APPS += ['debug_toolbar']
            MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    """,
    test_cases=[]
)

DJANGO_PAGINATION_DOS = SecurityPattern(
    id="DJANGO_PAGINATION_001",
    name="Large Pagination Size (DoS Risk)",
    category=VulnerabilityCategory.RESOURCE_MANAGEMENT,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Very large PAGE_SIZE (>1000) allows attackers to request huge datasets, "
        "causing high memory usage, slow responses, and potential denial of service."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_PAGINATION_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Large pagination size' AS finding,
            'MEDIUM' AS severity
        FROM nodes_assignment
        WHERE code LIKE '%PAGE_SIZE%'
          AND code ~ '[0-9]{4,}'  -- 4+ digit number (>=1000)
        LIMIT 5;
    """,
    cwe_ids=["CWE-400", "CWE-770"],
    remediation=(
        "1. Set reasonable PAGE_SIZE (10-100)\n"
        "2. Implement MAX_PAGE_SIZE limit\n"
        "3. REST_FRAMEWORK = {\n"
        "       'PAGE_SIZE': 20,\n"
        "       'MAX_PAGE_SIZE': 100,\n"
        "   }"
    ),
    example_code="""
        # VULNERABLE
        REST_FRAMEWORK = {
            'PAGE_SIZE': 10000,  # Too large!
        }

        # SECURE
        REST_FRAMEWORK = {
            'PAGE_SIZE': 20,
            'MAX_PAGE_SIZE': 100,
        }
    """,
    test_cases=[]
)

PYTHON_YAML_UNSAFE = SecurityPattern(
    id="PYTHON_YAML_001",
    name="Unsafe YAML Loading",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "yaml.load() without specifying Loader can execute arbitrary Python code. "
        "Use yaml.safe_load() for untrusted data."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'PYTHON_YAML_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Unsafe YAML loading' AS finding,
            'MEDIUM' AS severity
        FROM nodes_call
        WHERE name = 'load'
          AND code LIKE '%yaml%'
          AND code NOT LIKE '%Loader%'
          AND code NOT LIKE '%safe_load%'
        LIMIT 20;
    """,
    cwe_ids=["CWE-502", "CWE-20"],
    remediation=(
        "1. Use yaml.safe_load() for untrusted data\n"
        "2. Or specify Loader: yaml.load(data, Loader=yaml.SafeLoader)\n"
        "3. Never use yaml.load() with user input"
    ),
    example_code="""
        # VULNERABLE
        data = yaml.load(user_input)  # RCE possible!

        # SECURE
        data = yaml.safe_load(user_input)
        data = yaml.load(user_input, Loader=yaml.SafeLoader)
    """,
    test_cases=[]
)

PYTHON_SENSITIVE_LOGGING = SecurityPattern(
    id="PYTHON_LOGGING_001",
    name="Sensitive Data in Logs",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Logging passwords, tokens, or personal data exposes sensitive information "
        "in log files, potentially accessible to unauthorized parties."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'PYTHON_LOGGING_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Potential sensitive data in logs' AS finding,
            'MEDIUM' AS severity
        FROM nodes_call
        WHERE name IN ('info', 'debug', 'warning', 'error', 'critical', 'log', 'print')
          AND (LOWER(code) LIKE '%password%'
               OR LOWER(code) LIKE '%token%'
               OR LOWER(code) LIKE '%secret%'
               OR LOWER(code) LIKE '%api_key%'
               OR LOWER(code) LIKE '%credit_card%')
        LIMIT 20;
    """,
    cwe_ids=["CWE-532", "CWE-117"],
    remediation=(
        "1. Never log passwords, tokens, or PII\n"
        "2. Use log scrubbing/filtering\n"
        "3. Log identifiers instead of sensitive values\n"
        "4. logger.info(f'User {user_id} logged in')  # Not password"
    ),
    example_code="""
        # VULNERABLE
        logger.info(f"User login: {username}, password: {password}")
        print(f"API token: {api_token}")

        # SECURE
        logger.info(f"User {user_id} logged in successfully")
        logger.debug(f"API request with token ending in ...{token[-4:]}")
    """,
    test_cases=[]
)

DJANGO_DEBUG_PERMISSION = SecurityPattern(
    id="DJANGO_DEBUG_PERM_001",
    name="Debug-Based Permission Check",
    category=VulnerabilityCategory.ACCESS_CONTROL,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Permission classes that grant access based on DEBUG setting are dangerous. "
        "If DEBUG accidentally becomes True in production, access controls are bypassed."
    ),
    cpgql_query="""
        SELECT DISTINCT
            'DJANGO_DEBUG_PERM_001' AS pattern_id,
            filename,
            line_number,
            code,
            'Permission based on DEBUG setting' AS finding,
            'HIGH' AS severity
        FROM nodes_method
        WHERE name LIKE '%permission%'
          AND code LIKE '%DEBUG%'
          AND code LIKE '%return%'
        LIMIT 10;
    """,
    cwe_ids=["CWE-489", "CWE-306"],
    remediation=(
        "1. Never use DEBUG in permission checks\n"
        "2. Use proper role-based access control\n"
        "3. Remove debug permission classes\n"
        "4. Use Django's built-in permission system"
    ),
    example_code="""
        # VULNERABLE
        class DebugPermission(BasePermission):
            def has_permission(self, request, view):
                return settings.DEBUG  # Bad!

        # SECURE
        class IsAdminUser(BasePermission):
            def has_permission(self, request, view):
                return request.user and request.user.is_staff
    """,
    test_cases=[]
)


# ============================================================================
# FILE-BASED PATTERNS (for direct scanning without CPG)
# ============================================================================

FILE_PATTERNS: Dict[str, FilePattern] = {
    "django_secret_key": FilePattern(
        id="FILE_DJANGO_SECRET_001",
        name="Hardcoded SECRET_KEY (File Scan)",
        category=VulnerabilityCategory.AUTHENTICATION,
        severity=VulnerabilitySeverity.CRITICAL,
        description="Django SECRET_KEY hardcoded in settings file",
        file_pattern="**/settings*.py",
        regex=re.compile(
            r"SECRET_KEY\s*=\s*['\"][^'\"]{10,}['\"]",
            re.IGNORECASE
        ),
        negative_regex=re.compile(r"os\.environ|getenv|config\("),
        cwe_ids=["CWE-798"],
        remediation="Use environment variable: SECRET_KEY = os.environ['SECRET_KEY']",
        example_vulnerable="SECRET_KEY = 'django-insecure-key'",
        example_secure="SECRET_KEY = os.environ['SECRET_KEY']"
    ),
    "django_debug_true": FilePattern(
        id="FILE_DJANGO_DEBUG_001",
        name="DEBUG=True (File Scan)",
        category=VulnerabilityCategory.CONFIGURATION,
        severity=VulnerabilitySeverity.CRITICAL,
        description="Django DEBUG mode enabled by default",
        file_pattern="**/settings*.py",
        regex=re.compile(
            r"DEBUG\s*=\s*(True|os\.environ\.get\s*\([^,]+,\s*(True|'True'|\"True\"|1)\s*\))",
            re.IGNORECASE
        ),
        cwe_ids=["CWE-489"],
        remediation="Set DEBUG=False in production, use env var without True default"
    ),
    "cors_all_origins": FilePattern(
        id="FILE_CORS_001",
        name="CORS Allow All (File Scan)",
        category=VulnerabilityCategory.CONFIGURATION,
        severity=VulnerabilitySeverity.HIGH,
        description="CORS configured to allow all origins",
        file_pattern="**/settings*.py",
        regex=re.compile(r"CORS_ALLOW_ALL_ORIGINS\s*=\s*True", re.IGNORECASE),
        cwe_ids=["CWE-346"],
        remediation="Set CORS_ALLOW_ALL_ORIGINS=False, use CORS_ALLOWED_ORIGINS list"
    ),
    "allowed_hosts_wildcard": FilePattern(
        id="FILE_HOSTS_001",
        name="ALLOWED_HOSTS Wildcard (File Scan)",
        category=VulnerabilityCategory.CONFIGURATION,
        severity=VulnerabilitySeverity.HIGH,
        description="ALLOWED_HOSTS contains wildcard",
        file_pattern="**/settings*.py",
        regex=re.compile(r"ALLOWED_HOSTS\s*=.*\*", re.IGNORECASE),
        cwe_ids=["CWE-942"],
        remediation="Specify explicit hostnames in ALLOWED_HOSTS"
    ),
    "jwt_long_expiry": FilePattern(
        id="FILE_JWT_001",
        name="JWT Long Expiry (File Scan)",
        category=VulnerabilityCategory.AUTHENTICATION,
        severity=VulnerabilitySeverity.HIGH,
        description="JWT access token lifetime too long (days/weeks)",
        file_pattern="**/settings*.py",
        regex=re.compile(r"ACCESS_TOKEN_LIFETIME.*timedelta\s*\(\s*(days|weeks)", re.IGNORECASE),
        cwe_ids=["CWE-613"],
        remediation="Set ACCESS_TOKEN_LIFETIME to minutes, use refresh tokens"
    ),
    "default_db_password": FilePattern(
        id="FILE_DB_001",
        name="Default DB Password (File Scan)",
        category=VulnerabilityCategory.AUTHENTICATION,
        severity=VulnerabilitySeverity.HIGH,
        description="Default database password in settings",
        file_pattern="**/settings*.py",
        regex=re.compile(
            r"['\"]PASSWORD['\"]\s*:.*(?:get\s*\([^)]*|default\s*=\s*)['\"]?(postgres|admin|root|password|123456)['\"]?",
            re.IGNORECASE
        ),
        cwe_ids=["CWE-798"],
        remediation="Remove default password fallback, require DB_PASSWORD env var"
    ),
    "debug_toolbar": FilePattern(
        id="FILE_TOOLBAR_001",
        name="Debug Toolbar (File Scan)",
        category=VulnerabilityCategory.CONFIGURATION,
        severity=VulnerabilitySeverity.MEDIUM,
        description="Django Debug Toolbar unconditionally enabled",
        file_pattern="**/settings*.py",
        regex=re.compile(r"['\"]debug_toolbar['\"]", re.IGNORECASE),
        negative_regex=re.compile(r"if\s+(DEBUG|settings\.DEBUG)"),
        cwe_ids=["CWE-489"],
        remediation="Enable debug_toolbar only when DEBUG is True"
    ),
    "pickle_load": FilePattern(
        id="FILE_PICKLE_001",
        name="Pickle Load (File Scan)",
        category=VulnerabilityCategory.INPUT_VALIDATION,
        severity=VulnerabilitySeverity.CRITICAL,
        description="Unsafe pickle deserialization",
        file_pattern="**/*.py",
        regex=re.compile(r"pickle\.(load|loads)\s*\("),
        cwe_ids=["CWE-502"],
        remediation="Use json.loads() or other safe serialization"
    ),
    "eval_exec": FilePattern(
        id="FILE_EVAL_001",
        name="eval/exec Usage (File Scan)",
        category=VulnerabilityCategory.INJECTION,
        severity=VulnerabilitySeverity.CRITICAL,
        description="Code execution via eval/exec",
        file_pattern="**/*.py",
        regex=re.compile(r"\b(eval|exec)\s*\("),
        negative_regex=re.compile(r"ast\.literal_eval"),
        cwe_ids=["CWE-94"],
        remediation="Use ast.literal_eval() or proper parsers"
    ),
    "shell_true": FilePattern(
        id="FILE_SHELL_001",
        name="subprocess shell=True (File Scan)",
        category=VulnerabilityCategory.INJECTION,
        severity=VulnerabilitySeverity.HIGH,
        description="Subprocess with shell=True",
        file_pattern="**/*.py",
        regex=re.compile(r"subprocess\.\w+\s*\([^)]*shell\s*=\s*True"),
        cwe_ids=["CWE-78"],
        remediation="Use shell=False with argument list"
    ),
    "path_traversal": FilePattern(
        id="FILE_PATH_001",
        name="Path Traversal (File Scan)",
        category=VulnerabilityCategory.INPUT_VALIDATION,
        severity=VulnerabilitySeverity.HIGH,
        description="File operation without path validation",
        file_pattern="**/*.py",
        regex=re.compile(r"os\.(remove|unlink|rmdir)\s*\(.*join.*\)"),
        negative_regex=re.compile(r"realpath|abspath"),
        cwe_ids=["CWE-22"],
        remediation="Validate paths with os.path.realpath() and check prefix"
    ),
    "secret_key_fallback": FilePattern(
        id="FILE_SECRET_FALLBACK_001",
        name="SECRET_KEY with Fallback (File Scan)",
        category=VulnerabilityCategory.AUTHENTICATION,
        severity=VulnerabilitySeverity.CRITICAL,
        description="SECRET_KEY with insecure fallback value",
        file_pattern="**/settings*.py",
        regex=re.compile(
            r"SECRET_KEY\s*=\s*os\.environ\.get\s*\(\s*['\"][^'\"]+['\"]\s*,\s*['\"][^'\"]{5,}['\"]",
            re.IGNORECASE
        ),
        cwe_ids=["CWE-798"],
        remediation="Remove fallback: SECRET_KEY = os.environ['SECRET_KEY']"
    ),
    "debug_permission": FilePattern(
        id="FILE_DEBUG_PERM_001",
        name="Debug Permission (File Scan)",
        category=VulnerabilityCategory.ACCESS_CONTROL,
        severity=VulnerabilitySeverity.HIGH,
        description="Permission check based on DEBUG setting",
        file_pattern="**/permissions*.py",
        regex=re.compile(r"return\s+(settings\.)?DEBUG"),
        cwe_ids=["CWE-489", "CWE-306"],
        remediation="Never use DEBUG in permission checks, use proper RBAC"
    ),
    "large_page_size": FilePattern(
        id="FILE_PAGESIZE_001",
        name="Large PAGE_SIZE (File Scan)",
        category=VulnerabilityCategory.RESOURCE_MANAGEMENT,
        severity=VulnerabilitySeverity.MEDIUM,
        description="REST_FRAMEWORK PAGE_SIZE too large (DoS risk)",
        file_pattern="**/settings*.py",
        regex=re.compile(r"['\"]PAGE_SIZE['\"]\s*:\s*(\d{4,})"),
        cwe_ids=["CWE-400", "CWE-770"],
        remediation="Set PAGE_SIZE to reasonable value (10-100), add MAX_PAGE_SIZE"
    ),
}


# ============================================================================
# PATTERN REGISTRIES
# ============================================================================

# All CPGQL-based security patterns for Python/Django
PYTHON_DJANGO_PATTERNS: Dict[str, SecurityPattern] = {
    # Critical
    "DJANGO_DEBUG_MODE": DJANGO_DEBUG_MODE,
    "DJANGO_SECRET_KEY_HARDCODED": DJANGO_SECRET_KEY_HARDCODED,
    "PYTHON_PICKLE_DESERIALIZATION": PYTHON_PICKLE_DESERIALIZATION,
    "PYTHON_EVAL_EXEC": PYTHON_EVAL_EXEC,
    "PYTHON_SQL_INJECTION": PYTHON_SQL_INJECTION,
    # High
    "DJANGO_CORS_ALL_ORIGINS": DJANGO_CORS_ALL_ORIGINS,
    "DJANGO_ALLOWED_HOSTS_WILDCARD": DJANGO_ALLOWED_HOSTS_WILDCARD,
    "JWT_LONG_EXPIRY": JWT_LONG_EXPIRY,
    "PYTHON_PATH_TRAVERSAL": PYTHON_PATH_TRAVERSAL,
    "DJANGO_CSRF_DISABLED": DJANGO_CSRF_DISABLED,
    "PYTHON_SUBPROCESS_SHELL": PYTHON_SUBPROCESS_SHELL,
    "DJANGO_DB_CREDENTIALS": DJANGO_DB_CREDENTIALS,
    "DJANGO_DEBUG_PERMISSION": DJANGO_DEBUG_PERMISSION,
    # Medium
    "DJANGO_DEBUG_TOOLBAR": DJANGO_DEBUG_TOOLBAR,
    "DJANGO_PAGINATION_DOS": DJANGO_PAGINATION_DOS,
    "PYTHON_YAML_UNSAFE": PYTHON_YAML_UNSAFE,
    "PYTHON_SENSITIVE_LOGGING": PYTHON_SENSITIVE_LOGGING,
}


def get_python_patterns() -> Dict[str, SecurityPattern]:
    """Get all Python/Django security patterns."""
    return PYTHON_DJANGO_PATTERNS.copy()


def get_file_patterns() -> Dict[str, FilePattern]:
    """Get all file-based scanning patterns."""
    return FILE_PATTERNS.copy()


def get_critical_python_patterns() -> List[SecurityPattern]:
    """Get critical severity Python patterns."""
    return [p for p in PYTHON_DJANGO_PATTERNS.values()
            if p.severity == VulnerabilitySeverity.CRITICAL]


def get_high_python_patterns() -> List[SecurityPattern]:
    """Get high severity Python patterns."""
    return [p for p in PYTHON_DJANGO_PATTERNS.values()
            if p.severity == VulnerabilitySeverity.HIGH]


__all__ = [
    'PYTHON_DJANGO_PATTERNS',
    'FILE_PATTERNS',
    'FilePattern',
    'get_python_patterns',
    'get_file_patterns',
    'get_critical_python_patterns',
    'get_high_python_patterns',
]
