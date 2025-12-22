"""
Kotlin Security Patterns

Patterns for detecting vulnerabilities specific to Kotlin and Android:
- SQL injection in Room/ContentProvider
- WebView JavaScript injection
- Intent redirection vulnerabilities
- Insecure data storage
- Hardcoded secrets

CWE-78, CWE-89, CWE-79, CWE-200, CWE-798, CWE-927
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


SQL_INJECTION_KOTLIN_PATTERN = SecurityPattern(
    id="KT_SQL_001",
    name="SQL Injection in Android",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL injection via string concatenation in rawQuery, execSQL, or "
        "ContentProvider queries. Use parameterized queries."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SQL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('rawQuery', 'execSQL', 'query', 'delete', 'update')
          AND (nc.code LIKE '%+%' OR nc.code LIKE '%$%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use parameterized queries with selectionArgs\n"
        "2. Use Room DAO with @Query annotations\n"
        "3. Never concatenate user input in SQL\n"
        "4. Use ContentResolver with selection args"
    ),
    example_code="""
        // VULNERABLE
        db.rawQuery("SELECT * FROM users WHERE id = $userId", null)
        db.execSQL("DELETE FROM users WHERE name = '" + name + "'")

        // SECURE
        db.rawQuery("SELECT * FROM users WHERE id = ?", arrayOf(userId))
        // Room DAO
        @Query("SELECT * FROM users WHERE id = :userId")
        fun getUser(userId: String): User
    """,
    test_cases=[
        {"name": "rawQuery with concat", "method": "getUser", "expected": True, "contains": ["rawQuery", "+"]}
    ]
)


WEBVIEW_XSS_PATTERN = SecurityPattern(
    id="KT_WEBVIEW_001",
    name="WebView JavaScript Injection",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "JavaScript injection in WebView via loadUrl with javascript: scheme "
        "or evaluateJavascript with unsanitized input."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'WEBVIEW_XSS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('loadUrl', 'evaluateJavascript', 'loadData',
                          'loadDataWithBaseURL', 'addJavascriptInterface')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-79"],
    remediation=(
        "1. Sanitize all data passed to JavaScript\n"
        "2. Disable JavaScript if not needed\n"
        "3. Use @JavascriptInterface carefully with API 17+\n"
        "4. Validate URLs before loading"
    ),
    example_code="""
        // VULNERABLE
        webView.loadUrl("javascript:updateData('$userInput')")
        webView.addJavascriptInterface(MyInterface(), "Android")

        // SECURE
        val sanitized = userInput.replace("'", "\\\\'")
        webView.evaluateJavascript("updateData('$sanitized')") { }
    """,
    test_cases=[
        {"name": "loadUrl with javascript", "method": "updateWebView", "expected": True, "contains": ["loadUrl", "javascript"]}
    ]
)


INTENT_REDIRECTION_PATTERN = SecurityPattern(
    id="KT_INTENT_001",
    name="Intent Redirection Vulnerability",
    category=VulnerabilityCategory.ACCESS_CONTROL,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Intent redirection when an exported component passes received intents "
        "to startActivity without validation, allowing privilege escalation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INTENT_REDIRECTION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('startActivity', 'startActivityForResult', 'startService',
                          'sendBroadcast')
          AND nc.code LIKE '%getParcelableExtra%'
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-927", "CWE-926"],
    remediation=(
        "1. Validate intent targets before forwarding\n"
        "2. Use explicit intents with component name\n"
        "3. Set exported=false for internal components\n"
        "4. Check caller permissions"
    ),
    example_code="""
        // VULNERABLE
        val forwarded = intent.getParcelableExtra<Intent>("next")
        startActivity(forwarded)

        // SECURE
        val forwarded = intent.getParcelableExtra<Intent>("next")
        if (forwarded?.component?.packageName == packageName) {
            startActivity(forwarded)
        }
    """,
    test_cases=[
        {"name": "Forward parcelable intent", "method": "handleIntent", "expected": True, "contains": ["getParcelableExtra", "startActivity"]}
    ]
)


INSECURE_STORAGE_PATTERN = SecurityPattern(
    id="KT_STORAGE_001",
    name="Insecure Data Storage",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Sensitive data stored in SharedPreferences, files, or databases "
        "without encryption, accessible to rooted devices or backup extraction."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_STORAGE' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('putString', 'putInt', 'edit', 'getSharedPreferences')
          AND (nc.code LIKE '%password%'
               OR nc.code LIKE '%token%'
               OR nc.code LIKE '%secret%'
               OR nc.code LIKE '%key%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-200", "CWE-312", "CWE-522"],
    remediation=(
        "1. Use EncryptedSharedPreferences\n"
        "2. Use Android Keystore for cryptographic keys\n"
        "3. Set android:allowBackup=false for sensitive apps\n"
        "4. Use SQLCipher for encrypted databases"
    ),
    example_code="""
        // VULNERABLE
        val prefs = getSharedPreferences("user", MODE_PRIVATE)
        prefs.edit().putString("password", password).apply()

        // SECURE
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        val prefs = EncryptedSharedPreferences.create(
            context, "secure_prefs", masterKey, ...)
        prefs.edit().putString("password", password).apply()
    """,
    test_cases=[
        {"name": "Store password in prefs", "method": "saveCredentials", "expected": True, "contains": ["putString", "password"]}
    ]
)


HARDCODED_SECRETS_KOTLIN_PATTERN = SecurityPattern(
    id="KT_SECRET_001",
    name="Hardcoded Secrets in Kotlin",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "API keys, passwords, or tokens hardcoded in Kotlin source code. "
        "Can be extracted from APK decompilation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nl.id,
            nl.value AS literal_value,
            nl.method_full_name AS full_name,
            nl.filename,
            nl.line_number,
            nl.code,
            'HARDCODED_SECRET' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_literal nl
        WHERE (nl.code LIKE '%API_KEY%'
               OR nl.code LIKE '%apiKey%'
               OR nl.code LIKE '%SECRET%'
               OR nl.code LIKE '%password%'
               OR nl.code LIKE '%token%')
          AND nl.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-798", "CWE-259"],
    remediation=(
        "1. Use BuildConfig for build-time secrets\n"
        "2. Fetch secrets from secure backend\n"
        "3. Use Android Keystore for local secrets\n"
        "4. Use NDK for obfuscated secrets (limited protection)"
    ),
    example_code="""
        // VULNERABLE
        const val API_KEY = "sk-1234567890abcdef"
        private val password = "admin123"

        // SECURE
        val apiKey = BuildConfig.API_KEY  // From gradle.properties
        // Or fetch from secure backend
        val apiKey = secureApi.getApiKey()
    """,
    test_cases=[
        {"name": "Hardcoded API key", "method": "init", "expected": True, "contains": ["API_KEY"]}
    ]
)


BROADCAST_RECEIVER_PATTERN = SecurityPattern(
    id="KT_BROADCAST_001",
    name="Insecure Broadcast Receiver",
    category=VulnerabilityCategory.ACCESS_CONTROL,
    severity=VulnerabilitySeverity.MEDIUM,
    description=(
        "Exported BroadcastReceiver without permission protection can receive "
        "intents from malicious apps."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_BROADCAST' AS vulnerability_type,
            'MEDIUM' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('registerReceiver', 'sendBroadcast', 'sendOrderedBroadcast')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-927"],
    remediation=(
        "1. Use LocalBroadcastManager for internal broadcasts\n"
        "2. Set android:exported=false for receivers\n"
        "3. Use custom permissions for exported receivers\n"
        "4. Validate intent data before processing"
    ),
    example_code="""
        // VULNERABLE
        registerReceiver(receiver, IntentFilter("com.app.ACTION"))

        // SECURE
        LocalBroadcastManager.getInstance(context)
            .registerReceiver(receiver, IntentFilter("com.app.ACTION"))
        // Or with permission
        registerReceiver(receiver, filter, "com.app.PERMISSION", null)
    """,
    test_cases=[
        {"name": "Register global receiver", "method": "onCreate", "expected": True, "contains": ["registerReceiver"]}
    ]
)


# Registry of Kotlin patterns
KOTLIN_PATTERNS: Dict[str, SecurityPattern] = {
    "SQL_INJECTION": SQL_INJECTION_KOTLIN_PATTERN,
    "WEBVIEW_XSS": WEBVIEW_XSS_PATTERN,
    "INTENT_REDIRECTION": INTENT_REDIRECTION_PATTERN,
    "INSECURE_STORAGE": INSECURE_STORAGE_PATTERN,
    "HARDCODED_SECRETS": HARDCODED_SECRETS_KOTLIN_PATTERN,
    "INSECURE_BROADCAST": BROADCAST_RECEIVER_PATTERN,
}
