"""
JavaScript/TypeScript Security Patterns

Patterns for detecting vulnerabilities specific to JavaScript and TypeScript:
- XSS via DOM manipulation
- Prototype pollution
- Insecure eval/Function usage
- npm dependency vulnerabilities
- Client-side injection

CWE-79 (XSS), CWE-94 (Code Injection), CWE-1321 (Prototype Pollution)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


XSS_DOM_PATTERN = SecurityPattern(
    id="JS_XSS_001",
    name="XSS via DOM Manipulation",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Cross-Site Scripting vulnerability via unsafe DOM manipulation methods "
        "such as innerHTML, outerHTML, document.write. User input is inserted "
        "directly into the DOM without sanitization."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'XSS_DOM' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('innerHTML', 'outerHTML', 'insertAdjacentHTML',
                          'document.write', 'document.writeln')
          AND nc.method_full_name NOT LIKE 'test_%'
          AND nc.method_full_name NOT LIKE '*test*'
        LIMIT 50;
    """,
    cwe_ids=["CWE-79"],
    remediation=(
        "1. Use textContent instead of innerHTML for text\n"
        "2. Use DOMPurify or similar library for sanitization\n"
        "3. Implement Content Security Policy (CSP)\n"
        "4. Use framework-safe methods (React JSX, Vue templates)"
    ),
    example_code="""
        // VULNERABLE
        element.innerHTML = userInput;
        document.write('<div>' + userInput + '</div>');

        // SECURE
        element.textContent = userInput;
        const clean = DOMPurify.sanitize(userInput);
        element.innerHTML = clean;
    """,
    test_cases=[
        {"name": "innerHTML assignment", "method": "renderContent", "expected": True, "contains": ["innerHTML"]},
        {"name": "textContent assignment", "method": "safeRender", "expected": False, "contains": ["textContent"]}
    ]
)


EVAL_INJECTION_PATTERN = SecurityPattern(
    id="JS_EVAL_001",
    name="Code Injection via eval/Function",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Dynamic code execution using eval(), Function(), or setTimeout/setInterval "
        "with string arguments. User input can lead to arbitrary code execution."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'EVAL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('eval', 'Function', 'setTimeout', 'setInterval')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-94", "CWE-95"],
    remediation=(
        "1. Never use eval() with user input\n"
        "2. Use JSON.parse() for JSON data\n"
        "3. Use function references instead of strings in setTimeout\n"
        "4. Implement strict CSP to block eval"
    ),
    example_code="""
        // VULNERABLE
        eval(userInput);
        new Function('return ' + userInput)();
        setTimeout('alert("' + msg + '")', 1000);

        // SECURE
        JSON.parse(userInput);
        setTimeout(() => alert(msg), 1000);
    """,
    test_cases=[
        {"name": "eval with user input", "method": "executeCode", "expected": True, "contains": ["eval"]}
    ]
)


PROTOTYPE_POLLUTION_PATTERN = SecurityPattern(
    id="JS_PROTO_001",
    name="Prototype Pollution",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Object prototype modification via unsafe deep merge, clone, or extend "
        "operations. Attackers can modify Object.prototype to affect all objects."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'PROTOTYPE_POLLUTION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.name IN ('merge', 'extend', 'deepMerge', 'assign', 'defaultsDeep')
               OR nc.code LIKE '%__proto__%'
               OR nc.code LIKE '%constructor%prototype%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-1321", "CWE-915"],
    remediation=(
        "1. Validate keys before assignment (__proto__, constructor, prototype)\n"
        "2. Use Object.create(null) for dictionaries\n"
        "3. Use Map instead of plain objects\n"
        "4. Freeze Object.prototype in critical code"
    ),
    example_code="""
        // VULNERABLE
        function merge(target, source) {
            for (const key in source) {
                target[key] = source[key];  // Can modify __proto__
            }
        }

        // SECURE
        function safeMerge(target, source) {
            for (const key of Object.keys(source)) {
                if (key === '__proto__' || key === 'constructor') continue;
                target[key] = source[key];
            }
        }
    """,
    test_cases=[
        {"name": "Deep merge function", "method": "deepMerge", "expected": True, "contains": ["merge"]}
    ]
)


SSRF_FETCH_PATTERN = SecurityPattern(
    id="JS_SSRF_001",
    name="Server-Side Request Forgery via fetch/axios",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "SSRF vulnerability when user-controlled URLs are passed to fetch, axios, "
        "or other HTTP libraries without URL validation."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SSRF' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('fetch', 'axios', 'request', 'got', 'http.get', 'https.get')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-918"],
    remediation=(
        "1. Validate URLs against allowlist of hosts\n"
        "2. Block internal IP ranges (127.0.0.1, 10.x, 192.168.x)\n"
        "3. Use URL parser to validate protocol (https only)\n"
        "4. Disable redirects or validate redirect targets"
    ),
    example_code="""
        // VULNERABLE
        const response = await fetch(userProvidedUrl);

        // SECURE
        const url = new URL(userProvidedUrl);
        if (!ALLOWED_HOSTS.includes(url.hostname)) {
            throw new Error('Host not allowed');
        }
        const response = await fetch(url);
    """,
    test_cases=[
        {"name": "fetch with user URL", "method": "proxyRequest", "expected": True, "contains": ["fetch"]}
    ]
)


INSECURE_CRYPTO_PATTERN = SecurityPattern(
    id="JS_CRYPTO_001",
    name="Weak Cryptographic Algorithm",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Use of weak or deprecated cryptographic algorithms like MD5, SHA1, "
        "DES, or custom encryption implementations."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'WEAK_CRYPTO' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.code LIKE '%MD5%'
               OR nc.code LIKE '%SHA1%'
               OR nc.code LIKE '%createHash%md5%'
               OR nc.code LIKE '%createHash%sha1%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-327", "CWE-328"],
    remediation=(
        "1. Use SHA-256 or SHA-3 for hashing\n"
        "2. Use AES-GCM for encryption\n"
        "3. Use bcrypt/scrypt/argon2 for passwords\n"
        "4. Use Web Crypto API or node:crypto with strong algorithms"
    ),
    example_code="""
        // VULNERABLE
        crypto.createHash('md5').update(data).digest('hex');

        // SECURE
        crypto.createHash('sha256').update(data).digest('hex');
        await crypto.subtle.digest('SHA-256', data);
    """,
    test_cases=[
        {"name": "MD5 hash", "method": "hashPassword", "expected": True, "contains": ["md5"]}
    ]
)


HARDCODED_SECRETS_PATTERN = SecurityPattern(
    id="JS_SECRET_001",
    name="Hardcoded Secrets in JavaScript",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Hardcoded API keys, passwords, tokens, or other secrets in JavaScript "
        "source code. These can be extracted from client-side bundles."
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
        WHERE (nl.code LIKE '%api_key%'
               OR nl.code LIKE '%apiKey%'
               OR nl.code LIKE '%secret%'
               OR nl.code LIKE '%password%'
               OR nl.code LIKE '%token%'
               OR nl.code LIKE '%private_key%')
          AND nl.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-798", "CWE-259"],
    remediation=(
        "1. Use environment variables for secrets\n"
        "2. Use secret management services (Vault, AWS Secrets Manager)\n"
        "3. Never commit secrets to version control\n"
        "4. Rotate exposed credentials immediately"
    ),
    example_code="""
        // VULNERABLE
        const API_KEY = 'sk-1234567890abcdef';
        const config = { password: 'admin123' };

        // SECURE
        const API_KEY = process.env.API_KEY;
        const config = { password: process.env.DB_PASSWORD };
    """,
    test_cases=[
        {"name": "Hardcoded API key", "method": "getClient", "expected": True, "contains": ["api_key"]}
    ]
)


# Registry of JavaScript/TypeScript patterns
JAVASCRIPT_PATTERNS: Dict[str, SecurityPattern] = {
    "XSS_DOM": XSS_DOM_PATTERN,
    "EVAL_INJECTION": EVAL_INJECTION_PATTERN,
    "PROTOTYPE_POLLUTION": PROTOTYPE_POLLUTION_PATTERN,
    "SSRF_FETCH": SSRF_FETCH_PATTERN,
    "INSECURE_CRYPTO": INSECURE_CRYPTO_PATTERN,
    "HARDCODED_SECRETS": HARDCODED_SECRETS_PATTERN,
}
