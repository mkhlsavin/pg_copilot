"""
C#/.NET Domain Plugin for CodeGraph.

Provides domain-specific configurations for C# and .NET applications
including security patterns for common enterprise vulnerabilities.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from src.domains.base import (
    DomainPlugin,
    SubsystemInfo,
    SecurityPattern,
    IntentPattern,
)


class CSharpPlugin(DomainPlugin):
    """
    Domain plugin for C#/.NET applications.

    Provides security patterns for:
    - SQL injection in ADO.NET/Entity Framework
    - XSS in ASP.NET MVC/Core
    - Insecure deserialization (BinaryFormatter)
    - Path traversal
    - XXE in XML processing
    - LDAP injection
    """

    @property
    def name(self) -> str:
        return "csharp"

    @property
    def display_name(self) -> str:
        return "C#/.NET"

    @property
    def description(self) -> str:
        return "C# and .NET application analysis (ASP.NET, Entity Framework, etc.)"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load C#/.NET subsystem definitions."""
        return {
            "controllers": SubsystemInfo(
                name="Controllers",
                description="ASP.NET MVC/WebAPI controllers",
                key_functions=[
                    "Get", "Post", "Put", "Delete", "Patch",
                    "HttpGet", "HttpPost", "ActionResult", "IActionResult",
                ],
                patterns=[r".*Controller$", r".*ApiController$"],
            ),
            "services": SubsystemInfo(
                name="Services",
                description="Business logic services",
                key_functions=[
                    "Execute", "Process", "Handle", "Invoke",
                ],
                patterns=[r".*Service$", r".*Manager$", r".*Handler$"],
            ),
            "data_access": SubsystemInfo(
                name="Data Access",
                description="Entity Framework and ADO.NET",
                key_functions=[
                    "SaveChanges", "SaveChangesAsync", "Add", "Update", "Remove",
                    "FromSqlRaw", "ExecuteSqlRaw", "SqlQuery",
                    "ExecuteReader", "ExecuteNonQuery", "ExecuteScalar",
                ],
                patterns=[r".*Repository$", r".*DbContext$"],
            ),
            "middleware": SubsystemInfo(
                name="Middleware",
                description="ASP.NET Core middleware pipeline",
                key_functions=[
                    "Invoke", "InvokeAsync", "Use", "UseMiddleware",
                ],
                patterns=[r".*Middleware$"],
            ),
            "authentication": SubsystemInfo(
                name="Authentication",
                description="Identity and authentication",
                key_functions=[
                    "SignInAsync", "SignOutAsync", "AuthenticateAsync",
                    "ValidateCredentials", "GenerateToken",
                ],
                patterns=[r".*AuthHandler$", r".*AuthService$"],
            ),
            "serialization": SubsystemInfo(
                name="Serialization",
                description="JSON/XML serialization",
                key_functions=[
                    "Serialize", "Deserialize", "JsonConvert",
                    "XmlSerializer", "DataContractSerializer",
                ],
                patterns=[r".*Serializer$", r".*Converter$"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load C#-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a C#/.NET security expert specializing in enterprise application security.
Focus on OWASP Top 10 vulnerabilities including SQL injection, XSS, insecure deserialization, and XXE.
Analyze ASP.NET controllers, Entity Framework queries, and XML processing for security vulnerabilities.""",
                "user_template": "Analyze the following C# code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a C#/.NET expert reviewing code for best practices.
Focus on .NET conventions, async/await patterns, SOLID principles, and security considerations.""",
                "user_template": "Review this C# code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load C#-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "injection", "xss", "deserialization", "xxe"],
                examples=["Find SQL injection vulnerabilities", "Check for XSS issues"],
                priority=10,
            ),
            "entityframework": IntentPattern(
                intent_id="entityframework",
                keywords=["dbcontext", "entity", "linq", "query", "ef"],
                examples=["Find raw SQL queries", "Show database contexts"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load C#/.NET security vulnerability patterns."""
        return [
            SecurityPattern(
                id="CS_SQL_INJECTION",
                name="SQL Injection in ADO.NET",
                description="SQL injection via string concatenation in SqlCommand",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["SqlCommand", "ExecuteReader", "ExecuteNonQuery", "FromSqlRaw", "+"],
                sinks=["SqlCommand", "ExecuteReader", "ExecuteNonQuery", "FromSqlRaw"],
                sources=["Request.Form", "Request.Query", "HttpContext"],
                sanitizers=["SqlParameter", "@", "FromSqlInterpolated"],
            ),
            SecurityPattern(
                id="CS_XSS",
                name="XSS in ASP.NET",
                description="Cross-site scripting via Html.Raw or disabled encoding",
                severity="high",
                cwe_id="CWE-79",
                indicators=["Html.Raw(", "WriteLiteral(", "HtmlString("],
                sinks=["Raw", "WriteLiteral", "HtmlString"],
                sources=["Model", "ViewBag", "ViewData"],
                sanitizers=["Html.Encode", "AntiXss"],
            ),
            SecurityPattern(
                id="CS_INSECURE_DESERIALIZATION",
                name="Insecure Deserialization",
                description="BinaryFormatter and similar unsafe deserializers",
                severity="critical",
                cwe_id="CWE-502",
                indicators=["BinaryFormatter", "NetDataContractSerializer", "SoapFormatter", "Deserialize"],
                sinks=["Deserialize", "UnsafeDeserialize", "ReadObject"],
            ),
            SecurityPattern(
                id="CS_PATH_TRAVERSAL",
                name="Path Traversal",
                description="Path traversal via user input in file operations",
                severity="high",
                cwe_id="CWE-22",
                indicators=["File.ReadAllText", "File.WriteAllText", "FileStream", "Path.Combine"],
                sinks=["ReadAllText", "WriteAllText", "Open", "FileStream"],
                sources=["Request.Form", "Request.Query"],
                sanitizers=["Path.GetFullPath", "StartsWith"],
            ),
            SecurityPattern(
                id="CS_XXE",
                name="XXE in XML Processing",
                description="XML External Entity injection with DTD processing enabled",
                severity="high",
                cwe_id="CWE-611",
                indicators=["XmlDocument", "XmlReader", "XmlTextReader", "Load", "LoadXml"],
                sanitizers=["DtdProcessing.Prohibit", "XmlResolver = null"],
            ),
            SecurityPattern(
                id="CS_LDAP_INJECTION",
                name="LDAP Injection",
                description="LDAP injection via unescaped filter strings",
                severity="high",
                cwe_id="CWE-90",
                indicators=["DirectorySearcher", "Filter", "FindAll", "FindOne"],
                sinks=["FindAll", "FindOne"],
                sources=["Request.Form", "Request.Query"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get C# taint source functions."""
        return [
            # ASP.NET request sources
            "Request.Form",
            "Request.Query",
            "Request.QueryString",
            "Request.Headers",
            "Request.Cookies",
            "Request.Body",
            "HttpContext.Request",
            # Model binding
            "FromBody",
            "FromQuery",
            "FromForm",
            "FromRoute",
            # Environment
            "Environment.GetEnvironmentVariable",
            "Configuration",
            # File/Stream
            "StreamReader.ReadToEnd",
            "File.ReadAllText",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get C# taint sink functions."""
        return [
            # SQL sinks
            "SqlCommand",
            "ExecuteReader",
            "ExecuteNonQuery",
            "ExecuteScalar",
            "FromSqlRaw",
            "ExecuteSqlRaw",
            # XSS sinks
            "Html.Raw",
            "WriteLiteral",
            "Response.Write",
            # Command injection
            "Process.Start",
            "ProcessStartInfo",
            # File operations
            "File.ReadAllText",
            "File.WriteAllText",
            "File.Delete",
            "FileStream",
            # Deserialization
            "BinaryFormatter.Deserialize",
            "JsonConvert.DeserializeObject",
            "XmlSerializer.Deserialize",
            # XML
            "XmlDocument.Load",
            "XmlDocument.LoadXml",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get C# vulnerability function mappings."""
        return {
            "SQL_INJECTION": ["SqlCommand", "ExecuteReader", "FromSqlRaw", "ExecuteSqlRaw"],
            "XSS": ["Html.Raw", "WriteLiteral", "Response.Write"],
            "COMMAND_INJECTION": ["Process.Start", "ProcessStartInfo"],
            "PATH_TRAVERSAL": ["File.ReadAllText", "File.WriteAllText", "FileStream"],
            "INSECURE_DESERIALIZATION": ["BinaryFormatter", "NetDataContractSerializer", "SoapFormatter"],
            "XXE": ["XmlDocument.Load", "XmlReader.Create", "XmlTextReader"],
            "LDAP_INJECTION": ["DirectorySearcher", "FindAll", "FindOne"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get C# concurrency functions."""
        return {
            "async_await": ["async", "await", "Task.Run", "Task.WhenAll", "Task.WhenAny"],
            "threading": ["Thread", "ThreadPool", "Start", "Join"],
            "locks": ["lock", "Monitor.Enter", "Monitor.Exit", "Mutex", "Semaphore"],
            "concurrent_collections": ["ConcurrentDictionary", "ConcurrentQueue", "ConcurrentBag"],
            "parallel": ["Parallel.For", "Parallel.ForEach", "AsParallel"],
        }
