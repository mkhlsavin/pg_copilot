"""
Kotlin/Android Domain Plugin for CodeGraph.

Provides domain-specific configurations for Kotlin and Android applications
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


class KotlinPlugin(DomainPlugin):
    """
    Domain plugin for Kotlin/Android applications.

    Provides security patterns for:
    - SQL injection in Room/SQLite
    - WebView JavaScript injection
    - Intent redirection vulnerabilities
    - Insecure data storage
    - Hardcoded secrets
    - Insecure broadcast receivers
    """

    @property
    def name(self) -> str:
        return "kotlin"

    @property
    def display_name(self) -> str:
        return "Kotlin/Android"

    @property
    def description(self) -> str:
        return "Kotlin and Android application analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load Kotlin/Android subsystem definitions."""
        return {
            "activities": SubsystemInfo(
                name="Activities",
                description="Android Activity components",
                key_functions=[
                    "onCreate", "onStart", "onResume", "onPause", "onStop", "onDestroy",
                    "startActivity", "startActivityForResult", "setContentView",
                ],
                patterns=[r".*Activity$"],
            ),
            "fragments": SubsystemInfo(
                name="Fragments",
                description="Android Fragment components",
                key_functions=[
                    "onCreateView", "onViewCreated", "onAttach", "onDetach",
                    "findNavController", "navigate",
                ],
                patterns=[r".*Fragment$"],
            ),
            "viewmodels": SubsystemInfo(
                name="ViewModels",
                description="Android ViewModel and LiveData",
                key_functions=[
                    "viewModelScope", "liveData", "MutableLiveData", "StateFlow",
                    "MutableStateFlow", "collect", "observe",
                ],
                patterns=[r".*ViewModel$"],
            ),
            "repositories": SubsystemInfo(
                name="Repositories",
                description="Data layer and repositories",
                key_functions=[
                    "Flow", "suspend", "withContext", "Dispatchers",
                    "query", "insert", "update", "delete",
                ],
                patterns=[r".*Repository$", r".*DataSource$"],
            ),
            "services": SubsystemInfo(
                name="Services",
                description="Android Service components",
                key_functions=[
                    "onStartCommand", "onBind", "startForeground",
                    "stopSelf", "bindService",
                ],
                patterns=[r".*Service$"],
            ),
            "receivers": SubsystemInfo(
                name="Broadcast Receivers",
                description="Android BroadcastReceiver components",
                key_functions=[
                    "onReceive", "registerReceiver", "sendBroadcast",
                    "LocalBroadcastManager",
                ],
                patterns=[r".*Receiver$"],
            ),
            "database": SubsystemInfo(
                name="Database",
                description="Room and SQLite database",
                key_functions=[
                    "@Query", "@Insert", "@Update", "@Delete",
                    "rawQuery", "execSQL", "Room.databaseBuilder",
                ],
                patterns=[r".*Dao$", r".*Database$"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load Kotlin-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a Kotlin/Android security expert specializing in mobile application security.
Focus on OWASP Mobile Top 10 including insecure data storage, WebView vulnerabilities, and intent handling.
Analyze Android components, Room queries, and IPC mechanisms for security vulnerabilities.""",
                "user_template": "Analyze the following Kotlin/Android code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a Kotlin/Android expert reviewing code for best practices.
Focus on Kotlin idioms, coroutines, Android architecture components, and security considerations.""",
                "user_template": "Review this Kotlin code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load Kotlin-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "webview", "intent", "storage", "secrets"],
                examples=["Find WebView vulnerabilities", "Check for insecure storage"],
                priority=10,
            ),
            "coroutines": IntentPattern(
                intent_id="coroutines",
                keywords=["coroutine", "suspend", "flow", "channel", "dispatcher"],
                examples=["Find coroutine issues", "Check Flow usage"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load Kotlin/Android security vulnerability patterns."""
        return [
            SecurityPattern(
                id="KT_SQL_INJECTION",
                name="SQL Injection in Android",
                description="SQL injection via rawQuery or execSQL with string concatenation",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["rawQuery", "execSQL", "query", "+", "$"],
                sinks=["rawQuery", "execSQL", "query"],
                sources=["intent.getStringExtra", "editText.text", "sharedPreferences"],
                sanitizers=["selectionArgs", "@Query"],
            ),
            SecurityPattern(
                id="KT_WEBVIEW_XSS",
                name="WebView JavaScript Injection",
                description="XSS via loadUrl with javascript: or evaluateJavascript",
                severity="high",
                cwe_id="CWE-79",
                indicators=["loadUrl", "evaluateJavascript", "loadData", "addJavascriptInterface"],
                sinks=["loadUrl", "evaluateJavascript", "loadData"],
                sources=["intent.getStringExtra", "editText.text"],
            ),
            SecurityPattern(
                id="KT_INTENT_REDIRECTION",
                name="Intent Redirection",
                description="Intent forwarding without validation allows privilege escalation",
                severity="high",
                cwe_id="CWE-927",
                indicators=["getParcelableExtra", "startActivity", "startService", "sendBroadcast"],
            ),
            SecurityPattern(
                id="KT_INSECURE_STORAGE",
                name="Insecure Data Storage",
                description="Sensitive data in SharedPreferences without encryption",
                severity="high",
                cwe_id="CWE-312",
                indicators=["SharedPreferences", "putString", "password", "token", "secret"],
                sanitizers=["EncryptedSharedPreferences", "MasterKey"],
            ),
            SecurityPattern(
                id="KT_HARDCODED_SECRETS",
                name="Hardcoded Secrets",
                description="API keys or passwords in source code",
                severity="critical",
                cwe_id="CWE-798",
                indicators=["API_KEY", "apiKey", "SECRET", "password", "token"],
            ),
            SecurityPattern(
                id="KT_INSECURE_BROADCAST",
                name="Insecure Broadcast Receiver",
                description="Exported receiver without permission protection",
                severity="medium",
                cwe_id="CWE-927",
                indicators=["registerReceiver", "sendBroadcast", "exported=true"],
                sanitizers=["LocalBroadcastManager", "permission"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get Kotlin/Android taint source functions."""
        return [
            # Intent extras
            "intent.getStringExtra",
            "intent.getIntExtra",
            "intent.getBundleExtra",
            "intent.getParcelableExtra",
            "intent.data",
            # UI input
            "editText.text",
            "textView.text",
            "EditText.getText",
            # Storage
            "sharedPreferences.getString",
            "getSharedPreferences",
            # Content providers
            "contentResolver.query",
            "cursor.getString",
            # Network
            "response.body",
            "retrofit",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get Kotlin/Android taint sink functions."""
        return [
            # SQL sinks
            "rawQuery",
            "execSQL",
            "query",
            "delete",
            "update",
            # WebView sinks
            "loadUrl",
            "evaluateJavascript",
            "loadData",
            "loadDataWithBaseURL",
            # Intent/IPC sinks
            "startActivity",
            "startActivityForResult",
            "startService",
            "sendBroadcast",
            "sendOrderedBroadcast",
            # Command execution
            "Runtime.exec",
            "ProcessBuilder",
            # File operations
            "FileOutputStream",
            "FileWriter",
            "openFileOutput",
            # Storage sinks
            "putString",
            "edit().putString",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get Kotlin vulnerability function mappings."""
        return {
            "SQL_INJECTION": ["rawQuery", "execSQL", "query"],
            "WEBVIEW_XSS": ["loadUrl", "evaluateJavascript", "loadData", "addJavascriptInterface"],
            "INTENT_REDIRECTION": ["startActivity", "startService", "sendBroadcast"],
            "INSECURE_STORAGE": ["SharedPreferences", "putString", "getSharedPreferences"],
            "COMMAND_INJECTION": ["Runtime.exec", "ProcessBuilder"],
            "PATH_TRAVERSAL": ["File", "FileInputStream", "openFileInput"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get Kotlin concurrency functions."""
        return {
            "coroutines": ["launch", "async", "runBlocking", "withContext", "suspend"],
            "dispatchers": ["Dispatchers.IO", "Dispatchers.Main", "Dispatchers.Default"],
            "flow": ["flow", "collect", "stateIn", "shareIn", "map", "filter"],
            "channels": ["Channel", "send", "receive", "consumeEach"],
            "scope": ["viewModelScope", "lifecycleScope", "GlobalScope", "CoroutineScope"],
        }
