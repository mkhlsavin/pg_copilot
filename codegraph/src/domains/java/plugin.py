"""
Java Domain Plugin for CodeGraph.

Provides domain-specific configurations for Java applications
including security patterns for common JVM vulnerabilities.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from src.domains.base import (
    DomainPlugin,
    SubsystemInfo,
    SecurityPattern,
    IntentPattern,
)


class JavaPlugin(DomainPlugin):
    """
    Domain plugin for Java applications.

    Provides security patterns for:
    - SQL injection via JDBC/JPA
    - JNDI injection
    - Unsafe deserialization
    - XXE (XML External Entity)
    - Path traversal
    - Command injection
    - LDAP injection
    """

    @property
    def name(self) -> str:
        return "java"

    @property
    def display_name(self) -> str:
        return "Java/JVM"

    @property
    def description(self) -> str:
        return "Java and JVM application analysis"

    def _load_subsystems(self) -> Dict[str, SubsystemInfo]:
        """Load Java subsystem definitions."""
        return {
            "controllers": SubsystemInfo(
                name="Controllers",
                description="Spring MVC/REST controllers",
                key_functions=[
                    "@Controller", "@RestController", "@RequestMapping",
                    "@GetMapping", "@PostMapping", "@PutMapping", "@DeleteMapping",
                    "@PathVariable", "@RequestBody", "@RequestParam",
                ],
                patterns=[r".*Controller$"],
            ),
            "services": SubsystemInfo(
                name="Services",
                description="Business logic services",
                key_functions=[
                    "@Service", "@Transactional", "@Async",
                    "@Cacheable", "@CacheEvict",
                ],
                patterns=[r".*Service$", r".*ServiceImpl$"],
            ),
            "repositories": SubsystemInfo(
                name="Repositories",
                description="Data access layer",
                key_functions=[
                    "@Repository", "JpaRepository", "CrudRepository",
                    "@Query", "EntityManager", "Session",
                    "createQuery", "createNativeQuery",
                ],
                patterns=[r".*Repository$", r".*Dao$"],
            ),
            "entities": SubsystemInfo(
                name="Entities",
                description="JPA/Hibernate entities",
                key_functions=[
                    "@Entity", "@Table", "@Column", "@Id",
                    "@OneToMany", "@ManyToOne", "@ManyToMany",
                ],
                patterns=[r".*Entity$"],
            ),
            "security": SubsystemInfo(
                name="Security",
                description="Spring Security components",
                key_functions=[
                    "@EnableWebSecurity", "WebSecurityConfigurerAdapter",
                    "UserDetailsService", "AuthenticationProvider",
                    "@PreAuthorize", "@Secured", "@RolesAllowed",
                ],
                patterns=[r".*Security.*", r".*Auth.*"],
            ),
            "configuration": SubsystemInfo(
                name="Configuration",
                description="Spring configuration classes",
                key_functions=[
                    "@Configuration", "@Bean", "@Value",
                    "@EnableAutoConfiguration", "@ComponentScan",
                ],
                patterns=[r".*Config$", r".*Configuration$"],
            ),
            "messaging": SubsystemInfo(
                name="Messaging",
                description="JMS, Kafka, RabbitMQ messaging",
                key_functions=[
                    "@JmsListener", "@KafkaListener", "@RabbitListener",
                    "JmsTemplate", "KafkaTemplate", "RabbitTemplate",
                ],
                patterns=[r".*Listener$", r".*Producer$", r".*Consumer$"],
            ),
        }

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load Java-specific prompts."""
        return {
            "security_audit": {
                "system": """You are a Java security expert specializing in application security.
Focus on OWASP Top 10 including injection, broken authentication, XSS, XXE, and deserialization.
Analyze Spring, JDBC, JPA code for security vulnerabilities.""",
                "user_template": "Analyze the following Java code for security vulnerabilities:\n{code}",
            },
            "code_review": {
                "system": """You are a Java expert reviewing code for best practices.
Focus on Java idioms, Spring patterns, JPA performance, and security considerations.""",
                "user_template": "Review this Java code:\n{code}",
            },
        }

    def _load_intent_patterns(self) -> Dict[str, IntentPattern]:
        """Load Java-specific intent patterns."""
        return {
            "security": IntentPattern(
                intent_id="security",
                keywords=["vulnerability", "security", "injection", "xxe", "deserialization", "jndi"],
                examples=["Find SQL injection", "Check for unsafe deserialization"],
                priority=10,
            ),
            "spring": IntentPattern(
                intent_id="spring",
                keywords=["spring", "bean", "controller", "service", "repository", "autowired"],
                examples=["Find Spring beans", "Analyze controllers"],
                priority=5,
            ),
        }

    def _load_security_patterns(self) -> List[SecurityPattern]:
        """Load Java security vulnerability patterns."""
        return [
            SecurityPattern(
                id="JAVA_SQL_INJECTION",
                name="SQL Injection",
                description="SQL injection via string concatenation in JDBC or native queries",
                severity="critical",
                cwe_id="CWE-89",
                indicators=["executeQuery", "executeUpdate", "createNativeQuery", "+", "concat"],
                sinks=["executeQuery", "executeUpdate", "execute", "createNativeQuery"],
                sources=["getParameter", "getHeader", "getInputStream", "@RequestParam", "@PathVariable"],
                sanitizers=["PreparedStatement", "setParameter", "@Query"],
            ),
            SecurityPattern(
                id="JAVA_JNDI_INJECTION",
                name="JNDI Injection",
                description="JNDI lookup with user-controlled input (Log4Shell, etc.)",
                severity="critical",
                cwe_id="CWE-917",
                indicators=["lookup", "InitialContext", "Context", "ldap://", "rmi://"],
                sinks=["lookup"],
                sources=["getParameter", "getHeader", "logger.info", "logger.error"],
            ),
            SecurityPattern(
                id="JAVA_DESERIALIZATION",
                name="Unsafe Deserialization",
                description="ObjectInputStream.readObject() with untrusted data",
                severity="critical",
                cwe_id="CWE-502",
                indicators=["ObjectInputStream", "readObject", "readUnshared", "XMLDecoder"],
                sinks=["readObject", "readUnshared", "decode"],
                sanitizers=["ObjectInputFilter", "ValidatingObjectInputStream"],
            ),
            SecurityPattern(
                id="JAVA_XXE",
                name="XML External Entity (XXE)",
                description="XML parsing without disabling external entities",
                severity="high",
                cwe_id="CWE-611",
                indicators=["DocumentBuilderFactory", "SAXParserFactory", "XMLInputFactory", "parse"],
                sanitizers=["setFeature", "FEATURE_SECURE_PROCESSING", "disallow-doctype-decl"],
            ),
            SecurityPattern(
                id="JAVA_PATH_TRAVERSAL",
                name="Path Traversal",
                description="File operations with user-controlled paths",
                severity="high",
                cwe_id="CWE-22",
                indicators=["File", "FileInputStream", "FileOutputStream", "Paths.get", ".."],
                sinks=["FileInputStream", "FileOutputStream", "Files.read", "Files.write"],
                sources=["getParameter", "@PathVariable", "getHeader"],
                sanitizers=["normalize", "getCanonicalPath"],
            ),
            SecurityPattern(
                id="JAVA_COMMAND_INJECTION",
                name="Command Injection",
                description="OS command execution with user input",
                severity="critical",
                cwe_id="CWE-78",
                indicators=["Runtime.exec", "ProcessBuilder", "cmd", "sh -c"],
                sinks=["exec", "start", "command"],
                sources=["getParameter", "@PathVariable", "getHeader"],
            ),
            SecurityPattern(
                id="JAVA_LDAP_INJECTION",
                name="LDAP Injection",
                description="LDAP queries with unsanitized user input",
                severity="high",
                cwe_id="CWE-90",
                indicators=["search", "DirContext", "LdapContext", "filter"],
                sinks=["search"],
                sources=["getParameter", "@RequestParam"],
            ),
            SecurityPattern(
                id="JAVA_SSRF",
                name="Server-Side Request Forgery",
                description="HTTP requests with user-controlled URLs",
                severity="high",
                cwe_id="CWE-918",
                indicators=["URL", "HttpURLConnection", "RestTemplate", "WebClient"],
                sinks=["openConnection", "getForObject", "exchange", "retrieve"],
                sources=["getParameter", "@RequestParam", "getHeader"],
            ),
            SecurityPattern(
                id="JAVA_HARDCODED_SECRETS",
                name="Hardcoded Secrets",
                description="Passwords, API keys, or secrets in source code",
                severity="critical",
                cwe_id="CWE-798",
                indicators=["password", "secret", "apiKey", "api_key", "token", "credential"],
            ),
        ]

    def get_taint_sources(self) -> List[str]:
        """Get Java taint source functions."""
        return [
            # Servlet API
            "request.getParameter",
            "request.getParameterValues",
            "request.getHeader",
            "request.getInputStream",
            "request.getReader",
            "request.getCookies",
            "request.getPathInfo",
            "request.getQueryString",
            # Spring MVC
            "@RequestParam",
            "@PathVariable",
            "@RequestBody",
            "@RequestHeader",
            "@CookieValue",
            # Input streams
            "BufferedReader.readLine",
            "Scanner.next",
            "InputStream.read",
            # Database results
            "ResultSet.getString",
            "ResultSet.getObject",
            # Environment
            "System.getenv",
            "System.getProperty",
        ]

    def get_taint_sinks(self) -> List[str]:
        """Get Java taint sink functions."""
        return [
            # SQL sinks
            "Statement.executeQuery",
            "Statement.executeUpdate",
            "Statement.execute",
            "PreparedStatement.execute",
            "EntityManager.createNativeQuery",
            "Session.createQuery",
            # Command execution
            "Runtime.exec",
            "ProcessBuilder.command",
            "ProcessBuilder.start",
            # File operations
            "FileInputStream",
            "FileOutputStream",
            "FileWriter",
            "FileReader",
            "Files.read",
            "Files.write",
            # Deserialization
            "ObjectInputStream.readObject",
            "XMLDecoder.readObject",
            # XML parsing
            "DocumentBuilder.parse",
            "SAXParser.parse",
            "XMLStreamReader.next",
            # JNDI
            "Context.lookup",
            "InitialContext.lookup",
            # LDAP
            "DirContext.search",
            # HTTP
            "URL.openConnection",
            "HttpURLConnection.connect",
            "RestTemplate.getForObject",
            "WebClient.get",
            # Response
            "PrintWriter.print",
            "response.getWriter",
            "response.getOutputStream",
        ]

    def get_vulnerability_function_mappings(self) -> Dict[str, List[str]]:
        """Get Java vulnerability function mappings."""
        return {
            "SQL_INJECTION": [
                "executeQuery", "executeUpdate", "execute",
                "createNativeQuery", "createQuery",
            ],
            "JNDI_INJECTION": ["lookup", "InitialContext"],
            "DESERIALIZATION": ["readObject", "readUnshared", "XMLDecoder"],
            "XXE": ["parse", "DocumentBuilder", "SAXParser", "XMLStreamReader"],
            "COMMAND_INJECTION": ["exec", "ProcessBuilder", "start"],
            "PATH_TRAVERSAL": ["FileInputStream", "FileOutputStream", "Files.read"],
            "LDAP_INJECTION": ["search", "DirContext"],
            "SSRF": ["openConnection", "getForObject", "exchange", "WebClient"],
        }

    def get_concurrency_functions(self) -> Dict[str, List[str]]:
        """Get Java concurrency functions."""
        return {
            "threads": ["Thread.start", "Runnable.run", "Callable.call"],
            "executors": [
                "ExecutorService", "ThreadPoolExecutor", "submit", "execute",
                "Executors.newFixedThreadPool", "Executors.newCachedThreadPool",
            ],
            "synchronization": [
                "synchronized", "Lock.lock", "ReentrantLock",
                "Semaphore", "CountDownLatch", "CyclicBarrier",
            ],
            "concurrent_collections": [
                "ConcurrentHashMap", "CopyOnWriteArrayList",
                "BlockingQueue", "ConcurrentLinkedQueue",
            ],
            "completable_future": [
                "CompletableFuture", "thenApply", "thenCompose",
                "supplyAsync", "runAsync", "allOf", "anyOf",
            ],
        }
