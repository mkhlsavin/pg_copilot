"""
Swift Security Patterns

Patterns for detecting vulnerabilities specific to Swift and iOS/macOS:
- Keychain misuse
- Insecure data storage
- URL scheme hijacking
- Certificate pinning bypass
- Hardcoded secrets
- Jailbreak detection bypass

CWE-200, CWE-295, CWE-312, CWE-798, CWE-939
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


INSECURE_KEYCHAIN_PATTERN = SecurityPattern(
    id="SWIFT_KEYCHAIN_001",
    name="Insecure Keychain Usage",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Keychain items stored without proper access control or with "
        "kSecAttrAccessibleAlways, making them accessible when device is locked."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_KEYCHAIN' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('SecItemAdd', 'SecItemUpdate')
          AND (nc.code LIKE '%kSecAttrAccessibleAlways%'
               OR nc.code NOT LIKE '%kSecAttrAccessible%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-312", "CWE-522"],
    remediation=(
        "1. Use kSecAttrAccessibleWhenUnlockedThisDeviceOnly\n"
        "2. Use kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly\n"
        "3. Add kSecAttrAccessControl for biometric protection\n"
        "4. Never use kSecAttrAccessibleAlways"
    ),
    example_code="""
        // VULNERABLE
        let query: [String: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecValueData: password,
            kSecAttrAccessible: kSecAttrAccessibleAlways  // Bad!
        ]

        // SECURE
        let access = SecAccessControlCreateWithFlags(
            nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            .userPresence, nil)
        let query: [String: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecValueData: password,
            kSecAttrAccessControl: access!
        ]
    """,
    test_cases=[
        {"name": "Keychain with AccessibleAlways", "method": "storeSecret", "expected": True, "contains": ["SecItemAdd", "AccessibleAlways"]}
    ]
)


INSECURE_STORAGE_SWIFT_PATTERN = SecurityPattern(
    id="SWIFT_STORAGE_001",
    name="Insecure Data Storage",
    category=VulnerabilityCategory.CONFIGURATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Sensitive data stored in UserDefaults, plist files, or unencrypted "
        "Core Data without protection."
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
        WHERE nc.name IN ('set', 'setValue', 'setObject', 'synchronize')
          AND nc.code LIKE '%UserDefaults%'
          AND (nc.code LIKE '%password%'
               OR nc.code LIKE '%token%'
               OR nc.code LIKE '%secret%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-200", "CWE-312"],
    remediation=(
        "1. Use Keychain for sensitive data\n"
        "2. Use encrypted Core Data (NSPersistentStoreDescription)\n"
        "3. Never store secrets in UserDefaults\n"
        "4. Use Data Protection API (complete protection)"
    ),
    example_code="""
        // VULNERABLE
        UserDefaults.standard.set(password, forKey: "password")
        UserDefaults.standard.set(token, forKey: "authToken")

        // SECURE
        // Use Keychain instead
        let keychain = Keychain(service: "com.app.service")
        keychain["password"] = password
    """,
    test_cases=[
        {"name": "UserDefaults password", "method": "saveCredentials", "expected": True, "contains": ["UserDefaults", "password"]}
    ]
)


URL_SCHEME_HIJACKING_PATTERN = SecurityPattern(
    id="SWIFT_URL_001",
    name="URL Scheme Hijacking",
    category=VulnerabilityCategory.ACCESS_CONTROL,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Custom URL scheme handling without proper validation allows malicious "
        "apps to intercept or inject data."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'URL_SCHEME_HIJACKING' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('open', 'openURL', 'application')
          AND nc.code LIKE '%handleOpen%'
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-939", "CWE-749"],
    remediation=(
        "1. Use Universal Links instead of custom schemes\n"
        "2. Validate source app using sourceApplication\n"
        "3. Validate URL parameters before processing\n"
        "4. Use App-bound domains for sensitive actions"
    ),
    example_code="""
        // VULNERABLE
        func application(_ app: UIApplication, open url: URL,
                         options: [UIApplication.OpenURLOptionsKey : Any]) -> Bool {
            processDeepLink(url)  // No validation
            return true
        }

        // SECURE
        func application(_ app: UIApplication, open url: URL,
                         options: [UIApplication.OpenURLOptionsKey : Any]) -> Bool {
            guard let sourceApp = options[.sourceApplication] as? String,
                  allowedApps.contains(sourceApp) else { return false }
            guard url.host == "expected.host" else { return false }
            processDeepLink(url)
            return true
        }
    """,
    test_cases=[
        {"name": "URL handler without validation", "method": "handleOpenURL", "expected": True, "contains": ["openURL"]}
    ]
)


TLS_BYPASS_PATTERN = SecurityPattern(
    id="SWIFT_TLS_001",
    name="Certificate Pinning Bypass",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "TLS certificate validation disabled or App Transport Security (ATS) "
        "exceptions allowing insecure connections."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'TLS_BYPASS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.code LIKE '%serverTrustPolicy%'
               OR nc.code LIKE '%disableEvaluation%'
               OR nc.code LIKE '%trustAll%'
               OR nc.code LIKE '%allowsInvalidSSL%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-295"],
    remediation=(
        "1. Implement proper certificate pinning\n"
        "2. Do not add ATS exceptions for production\n"
        "3. Use TrustKit or Alamofire ServerTrustManager\n"
        "4. Pin to leaf certificate or public key"
    ),
    example_code="""
        // VULNERABLE
        let manager = ServerTrustManager(evaluators: [
            "api.example.com": DisabledEvaluator()
        ])

        // SECURE
        let manager = ServerTrustManager(evaluators: [
            "api.example.com": PinnedCertificatesTrustEvaluator(
                certificates: [certificateData],
                performDefaultValidation: true
            )
        ])
    """,
    test_cases=[
        {"name": "Disabled TLS evaluation", "method": "setupSession", "expected": True, "contains": ["DisabledEvaluator"]}
    ]
)


HARDCODED_SECRETS_SWIFT_PATTERN = SecurityPattern(
    id="SWIFT_SECRET_001",
    name="Hardcoded Secrets in Swift",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "API keys, passwords, or tokens hardcoded in Swift source code. "
        "Can be extracted from IPA analysis."
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
        WHERE (nl.code LIKE '%apiKey%'
               OR nl.code LIKE '%API_KEY%'
               OR nl.code LIKE '%secret%'
               OR nl.code LIKE '%password%'
               OR nl.code LIKE '%token%')
          AND nl.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-798", "CWE-259"],
    remediation=(
        "1. Fetch secrets from secure backend at runtime\n"
        "2. Use Keychain for local secret storage\n"
        "3. Use environment variables for build-time secrets\n"
        "4. Consider obfuscation (limited protection)"
    ),
    example_code="""
        // VULNERABLE
        let apiKey = "sk-1234567890abcdef"
        static let secret = "mySecretValue"

        // SECURE
        let apiKey = ProcessInfo.processInfo.environment["API_KEY"]
        // Or fetch from secure backend
        let apiKey = try await AuthService.shared.getApiKey()
    """,
    test_cases=[
        {"name": "Hardcoded API key", "method": "init", "expected": True, "contains": ["apiKey"]}
    ]
)


WEBVIEW_SWIFT_PATTERN = SecurityPattern(
    id="SWIFT_WEBVIEW_001",
    name="Insecure WKWebView Configuration",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "WKWebView with insecure JavaScript handling or allowing arbitrary "
        "file access via local URLs."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_WEBVIEW' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('loadFileURL', 'evaluateJavaScript', 'load')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-79", "CWE-200"],
    remediation=(
        "1. Validate URLs before loading\n"
        "2. Disable JavaScript if not needed\n"
        "3. Use allowingReadAccessTo carefully with loadFileURL\n"
        "4. Sanitize data passed to evaluateJavaScript"
    ),
    example_code="""
        // VULNERABLE
        webView.loadFileURL(userURL, allowingReadAccessTo: documentsDir)
        webView.evaluateJavaScript("update('\\(userInput)')")

        // SECURE
        guard userURL.host == "trusted.domain" else { return }
        let sanitized = userInput.addingPercentEncoding(...)
        webView.evaluateJavaScript("update('\\(sanitized ?? "")')")
    """,
    test_cases=[
        {"name": "WKWebView eval with user input", "method": "updateContent", "expected": True, "contains": ["evaluateJavaScript"]}
    ]
)


# Registry of Swift patterns
SWIFT_PATTERNS: Dict[str, SecurityPattern] = {
    "INSECURE_KEYCHAIN": INSECURE_KEYCHAIN_PATTERN,
    "INSECURE_STORAGE": INSECURE_STORAGE_SWIFT_PATTERN,
    "URL_SCHEME_HIJACKING": URL_SCHEME_HIJACKING_PATTERN,
    "TLS_BYPASS": TLS_BYPASS_PATTERN,
    "HARDCODED_SECRETS": HARDCODED_SECRETS_SWIFT_PATTERN,
    "INSECURE_WEBVIEW": WEBVIEW_SWIFT_PATTERN,
}
