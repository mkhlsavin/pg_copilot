"""
Swift/iOS Domain Plugin for CodeGraph.

Provides domain-specific configurations for Swift and iOS/macOS applications
including security patterns for common mobile vulnerabilities.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from src.domains.base import (
    DomainPlugin,
    SubsystemInfo,
    SecurityPattern,
    IntentPattern,
)


class SwiftPlugin(DomainPlugin):
    """
    Domain plugin for Swift/iOS applications.

    Provides security patterns for:
    - Keychain misuse
    - Insecure data storage
    - URL scheme hijacking
    - Certificate pinning bypass
    - Hardcoded secrets
    - Insecure WKWebView
    """

    @property
    def name(self) -> str:
        return "swift"

    @property
    def display_name(self) -> str:
        return "Swift/iOS"

    @property
    def description(self) -> str:
        return "Swift and iOS/macOS application analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load Swift/iOS subsystem definitions."""
        return {
            "viewcontrollers": SubsystemInfo(
                name="View Controllers",
                description="UIViewController and SwiftUI views",
                key_functions=[
                    "viewDidLoad", "viewWillAppear", "viewDidAppear",
                    "viewWillDisappear", "viewDidDisappear",
                    "body", "onAppear", "onDisappear",
                ],
                patterns=[r".*ViewController$", r".*View$"],
            ),
            "models": SubsystemInfo(
                name="Models",
                description="Data models and Codable types",
                key_functions=[
                    "init", "encode", "decode", "Codable", "Decodable",
                ],
                patterns=[r".*Model$", r".*Entity$"],
            ),
            "networking": SubsystemInfo(
                name="Networking",
                description="URLSession and network operations",
                key_functions=[
                    "URLSession", "dataTask", "downloadTask", "uploadTask",
                    "resume", "cancel", "Alamofire", "Moya",
                ],
                patterns=[r".*APIClient$", r".*NetworkManager$", r".*Service$"],
            ),
            "storage": SubsystemInfo(
                name="Storage",
                description="Data persistence (UserDefaults, Core Data, Keychain)",
                key_functions=[
                    "UserDefaults", "set", "object(forKey:", "CoreData",
                    "NSManagedObjectContext", "save", "fetch",
                ],
                patterns=[r".*Storage$", r".*Repository$", r".*Store$"],
            ),
            "keychain": SubsystemInfo(
                name="Keychain",
                description="Keychain Services for secure storage",
                key_functions=[
                    "SecItemAdd", "SecItemUpdate", "SecItemCopyMatching",
                    "SecItemDelete", "kSecClass", "kSecAttrAccessible",
                ],
                patterns=[r".*KeychainManager$", r".*KeychainWrapper$"],
            ),
            "authentication": SubsystemInfo(
                name="Authentication",
                description="Authentication and biometrics",
                key_functions=[
                    "LAContext", "evaluatePolicy", "canEvaluatePolicy",
                    "ASAuthorizationController", "signIn",
                ],
                patterns=[r".*AuthManager$", r".*AuthService$"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load Swift-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a Swift/iOS security expert specializing in mobile application security.
Focus on OWASP Mobile Top 10 including insecure data storage, TLS validation, and URL scheme handling.
Analyze Keychain usage, WKWebView configurations, and network security for vulnerabilities.""",
                "user_template": "Analyze the following Swift code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a Swift/iOS expert reviewing code for best practices.
Focus on Swift idioms, memory management, async/await, and security considerations.""",
                "user_template": "Review this Swift code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load Swift-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "keychain", "tls", "storage", "secrets"],
                examples=["Find Keychain issues", "Check for insecure storage"],
                priority=10,
            ),
            "concurrency": IntentPattern(
                intent_id="concurrency",
                keywords=["async", "await", "task", "actor", "dispatch"],
                examples=["Find async issues", "Check concurrency"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load Swift/iOS security vulnerability patterns."""
        return [
            SecurityPattern(
                id="SWIFT_INSECURE_KEYCHAIN",
                name="Insecure Keychain Usage",
                description="Keychain items without proper access control",
                severity="high",
                cwe_id="CWE-312",
                indicators=["SecItemAdd", "SecItemUpdate", "kSecAttrAccessibleAlways"],
                sinks=["SecItemAdd", "SecItemUpdate"],
                sanitizers=["kSecAttrAccessibleWhenUnlockedThisDeviceOnly", "SecAccessControl"],
            ),
            SecurityPattern(
                id="SWIFT_INSECURE_STORAGE",
                name="Insecure Data Storage",
                description="Sensitive data in UserDefaults without encryption",
                severity="high",
                cwe_id="CWE-312",
                indicators=["UserDefaults", "set(", "password", "token", "secret"],
                sinks=["set(", "setValue("],
                sources=["password", "token", "apiKey"],
            ),
            SecurityPattern(
                id="SWIFT_URL_SCHEME_HIJACKING",
                name="URL Scheme Hijacking",
                description="Custom URL scheme handling without validation",
                severity="high",
                cwe_id="CWE-939",
                indicators=["application(", "open url:", "handleOpen", "openURL"],
                sanitizers=["sourceApplication", "host =="],
            ),
            SecurityPattern(
                id="SWIFT_TLS_BYPASS",
                name="Certificate Pinning Bypass",
                description="Disabled TLS validation or ATS exceptions",
                severity="high",
                cwe_id="CWE-295",
                indicators=["DisabledEvaluator", "trustAll", "allowsInvalidSSL", "InsecureSkipVerify"],
                sanitizers=["PinnedCertificatesTrustEvaluator", "ServerTrustManager"],
            ),
            SecurityPattern(
                id="SWIFT_HARDCODED_SECRETS",
                name="Hardcoded Secrets",
                description="API keys or passwords in source code",
                severity="critical",
                cwe_id="CWE-798",
                indicators=["apiKey", "API_KEY", "secret", "password", "token"],
            ),
            SecurityPattern(
                id="SWIFT_INSECURE_WEBVIEW",
                name="Insecure WKWebView",
                description="WKWebView with unsafe JavaScript handling",
                severity="high",
                cwe_id="CWE-79",
                indicators=["loadFileURL", "evaluateJavaScript", "allowingReadAccessTo"],
                sinks=["evaluateJavaScript", "loadFileURL", "load"],
                sources=["userInput", "URL"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get Swift/iOS taint source functions."""
        return [
            # URL/Deep linking
            "url.queryItems",
            "URLComponents",
            "url.absoluteString",
            # User input
            "textField.text",
            "UITextField",
            "UIPasteboard",
            # Storage
            "UserDefaults.standard",
            "object(forKey:",
            # Network
            "URLSession.shared",
            "response.data",
            # Keychain
            "SecItemCopyMatching",
            # Environment
            "ProcessInfo.processInfo.environment",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get Swift/iOS taint sink functions."""
        return [
            # WebView sinks
            "evaluateJavaScript",
            "loadFileURL",
            "load",
            "loadHTMLString",
            # URL sinks
            "open",
            "openURL",
            "canOpenURL",
            # Storage sinks
            "set(",
            "setValue(",
            "synchronize",
            # Keychain sinks
            "SecItemAdd",
            "SecItemUpdate",
            # File sinks
            "write(to:",
            "FileManager",
            "createFile",
            # Network sinks
            "URLRequest",
            "dataTask",
            # Process sinks
            "Process",
            "launch",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get Swift vulnerability function mappings."""
        return {
            "INSECURE_KEYCHAIN": ["SecItemAdd", "SecItemUpdate", "kSecAttrAccessibleAlways"],
            "INSECURE_STORAGE": ["UserDefaults", "set(", "setValue("],
            "URL_SCHEME_HIJACKING": ["application(", "open url:", "openURL"],
            "TLS_BYPASS": ["DisabledEvaluator", "trustAll", "allowsInvalidSSL"],
            "WEBVIEW_XSS": ["evaluateJavaScript", "loadFileURL", "loadHTMLString"],
            "PATH_TRAVERSAL": ["FileManager", "contentsOfDirectory", "createFile"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get Swift concurrency functions."""
        return {
            "async_await": ["async", "await", "Task", "TaskGroup", "withTaskGroup"],
            "actors": ["actor", "nonisolated", "@MainActor", "isolated"],
            "dispatch": ["DispatchQueue", "async", "sync", "asyncAfter"],
            "combine": ["Publisher", "sink", "receive", "assign", "subscribe"],
            "operations": ["OperationQueue", "BlockOperation", "addOperation"],
        }
