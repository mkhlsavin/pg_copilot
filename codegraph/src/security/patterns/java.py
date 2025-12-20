"""
Java Security Patterns

Patterns for detecting vulnerabilities specific to Java/JVM applications:
- SQL injection in JDBC/JPA
- JNDI injection (Log4Shell, etc.)
- Unsafe deserialization
- XXE (XML External Entity)
- Path traversal
- Command injection
- LDAP injection
- SSRF (Server-Side Request Forgery)

CWE-22, CWE-78, CWE-89, CWE-90, CWE-502, CWE-611, CWE-798, CWE-917, CWE-918
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


SQL_INJECTION_JAVA_PATTERN = SecurityPattern(
    id="JAVA_SQL_001",
    name="SQL Injection in JDBC/JPA",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL injection via string concatenation in JDBC executeQuery/executeUpdate "
        "or JPA createNativeQuery. Use PreparedStatement or parameterized queries."
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
        WHERE nc.name IN ('executeQuery', 'executeUpdate', 'execute',
                          'createNativeQuery', 'createQuery')
          AND (nc.code LIKE '%+%' OR nc.code LIKE '%concat%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use PreparedStatement with parameterized queries\n"
        "2. Use JPA @Query with named parameters\n"
        "3. Never concatenate user input in SQL\n"
        "4. Use ORM methods (findById, save) instead of raw queries"
    ),
    example_code="""
        // VULNERABLE
        stmt.executeQuery("SELECT * FROM users WHERE id = " + userId);
        em.createNativeQuery("DELETE FROM users WHERE name = '" + name + "'");

        // SECURE
        PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
        ps.setString(1, userId);
        em.createQuery("SELECT u FROM User u WHERE u.name = :name")
          .setParameter("name", name);
    """,
    test_cases=[
        {"name": "executeQuery with concat", "method": "getUser", "expected": True, "contains": ["executeQuery", "+"]}
    ]
)


JNDI_INJECTION_PATTERN = SecurityPattern(
    id="JAVA_JNDI_001",
    name="JNDI Injection",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "JNDI lookup with user-controlled input can lead to remote code execution. "
        "This includes Log4Shell (CVE-2021-44228) and similar vulnerabilities."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'JNDI_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name = 'lookup'
          AND (nc.code LIKE '%ldap%' OR nc.code LIKE '%rmi%'
               OR nc.code LIKE '%+%' OR nc.code LIKE '%$%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-917", "CWE-74"],
    remediation=(
        "1. Never pass user input directly to JNDI lookup\n"
        "2. Use allowlist for JNDI names\n"
        "3. Disable JNDI lookups if not needed\n"
        "4. Update Log4j to 2.17.0+ and set log4j2.formatMsgNoLookups=true"
    ),
    example_code="""
        // VULNERABLE (Log4Shell)
        logger.info("User: " + userInput);  // if userInput contains ${jndi:ldap://...}
        ctx.lookup(userControlledString);

        // SECURE
        logger.info("User: {}", sanitize(userInput));
        // Use allowlist
        if (ALLOWED_NAMES.contains(name)) {
            ctx.lookup(name);
        }
    """,
    test_cases=[
        {"name": "lookup with variable", "method": "resolveName", "expected": True, "contains": ["lookup"]}
    ]
)


DESERIALIZATION_PATTERN = SecurityPattern(
    id="JAVA_DESER_001",
    name="Unsafe Deserialization",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "ObjectInputStream.readObject() with untrusted data can lead to RCE. "
        "Attackers can craft malicious serialized objects using gadget chains."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'DESERIALIZATION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('readObject', 'readUnshared', 'decode')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-502"],
    remediation=(
        "1. Avoid Java serialization for untrusted data\n"
        "2. Use JSON/XML with strict schema validation\n"
        "3. Implement ObjectInputFilter (Java 9+)\n"
        "4. Use ValidatingObjectInputStream from Apache Commons IO\n"
        "5. Remove vulnerable gadget libraries from classpath"
    ),
    example_code="""
        // VULNERABLE
        ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
        Object obj = ois.readObject();

        // SECURE (Java 9+)
        ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
            "com.myapp.*;!*"
        );
        ois.setObjectInputFilter(filter);
    """,
    test_cases=[
        {"name": "readObject call", "method": "deserialize", "expected": True, "contains": ["readObject"]}
    ]
)


XXE_PATTERN = SecurityPattern(
    id="JAVA_XXE_001",
    name="XML External Entity (XXE)",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "XML parsing without disabling external entities can lead to file disclosure, "
        "SSRF, or denial of service via billion laughs attack."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'XXE' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('parse', 'newDocumentBuilder', 'newSAXParser',
                          'createXMLStreamReader', 'unmarshal')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-611"],
    remediation=(
        "1. Disable external entities and DTDs:\n"
        "   factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);\n"
        "   factory.setFeature(\"http://apache.org/xml/features/disallow-doctype-decl\", true);\n"
        "2. Use defused XML parsers\n"
        "3. Validate and sanitize XML before parsing"
    ),
    example_code="""
        // VULNERABLE
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(inputStream);

        // SECURE
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    """,
    test_cases=[
        {"name": "XML parse without config", "method": "parseXml", "expected": True, "contains": ["parse"]}
    ]
)


PATH_TRAVERSAL_PATTERN = SecurityPattern(
    id="JAVA_PATH_001",
    name="Path Traversal",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "File operations with user-controlled paths without validation "
        "can allow reading/writing arbitrary files."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'PATH_TRAVERSAL' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('FileInputStream', 'FileOutputStream', 'FileReader',
                          'FileWriter', 'get', 'resolve')
          AND (nc.code LIKE '%getParameter%' OR nc.code LIKE '%@PathVariable%'
               OR nc.code LIKE '%+%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-22"],
    remediation=(
        "1. Use getCanonicalPath() and validate against base directory\n"
        "2. Reject paths containing '..' or absolute paths\n"
        "3. Use allowlist for filenames\n"
        "4. Use java.nio.file with proper path normalization"
    ),
    example_code="""
        // VULNERABLE
        String filename = request.getParameter("file");
        File file = new File("/uploads/" + filename);
        InputStream is = new FileInputStream(file);

        // SECURE
        String filename = request.getParameter("file");
        Path basePath = Paths.get("/uploads").toRealPath();
        Path filePath = basePath.resolve(filename).normalize();
        if (!filePath.startsWith(basePath)) {
            throw new SecurityException("Path traversal attempt");
        }
    """,
    test_cases=[
        {"name": "FileInputStream with param", "method": "readFile", "expected": True, "contains": ["FileInputStream"]}
    ]
)


COMMAND_INJECTION_PATTERN = SecurityPattern(
    id="JAVA_CMD_001",
    name="Command Injection",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "OS command execution with user-controlled input can lead to RCE."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'COMMAND_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('exec', 'command', 'start')
          AND (nc.code LIKE '%Runtime%' OR nc.code LIKE '%ProcessBuilder%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-78"],
    remediation=(
        "1. Avoid executing OS commands with user input\n"
        "2. Use allowlist for allowed commands and arguments\n"
        "3. Use ProcessBuilder with separate arguments (not shell)\n"
        "4. Escape shell metacharacters if unavoidable"
    ),
    example_code="""
        // VULNERABLE
        Runtime.getRuntime().exec("ping " + userInput);
        new ProcessBuilder("sh", "-c", "ping " + userInput).start();

        // SECURE (still risky, avoid if possible)
        ProcessBuilder pb = new ProcessBuilder("ping", "-c", "1", sanitize(host));
        pb.start();
    """,
    test_cases=[
        {"name": "Runtime.exec with variable", "method": "runCommand", "expected": True, "contains": ["exec"]}
    ]
)


LDAP_INJECTION_PATTERN = SecurityPattern(
    id="JAVA_LDAP_001",
    name="LDAP Injection",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "LDAP queries with unsanitized user input can bypass authentication "
        "or disclose sensitive directory information."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'LDAP_INJECTION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name = 'search'
          AND (nc.code LIKE '%DirContext%' OR nc.code LIKE '%LdapContext%')
          AND (nc.code LIKE '%+%' OR nc.code LIKE '%$%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-90"],
    remediation=(
        "1. Use parameterized LDAP queries\n"
        "2. Escape LDAP special characters: \\, *, (, ), NUL\n"
        "3. Use allowlist for search filters\n"
        "4. Limit search scope and results"
    ),
    example_code="""
        // VULNERABLE
        String filter = "(uid=" + username + ")";
        ctx.search("ou=users,dc=example,dc=com", filter, controls);

        // SECURE
        String escapedUser = LdapEncoder.filterEncode(username);
        String filter = "(uid=" + escapedUser + ")";
    """,
    test_cases=[
        {"name": "LDAP search with concat", "method": "findUser", "expected": True, "contains": ["search"]}
    ]
)


SSRF_PATTERN = SecurityPattern(
    id="JAVA_SSRF_001",
    name="Server-Side Request Forgery",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "HTTP requests with user-controlled URLs can access internal services, "
        "cloud metadata endpoints, or perform port scanning."
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
        WHERE nc.name IN ('openConnection', 'getForObject', 'postForObject',
                          'exchange', 'get', 'post')
          AND (nc.code LIKE '%URL%' OR nc.code LIKE '%RestTemplate%'
               OR nc.code LIKE '%WebClient%')
          AND (nc.code LIKE '%getParameter%' OR nc.code LIKE '%+%')
          AND nc.method_full_name NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-918"],
    remediation=(
        "1. Use allowlist for allowed hosts/URLs\n"
        "2. Block private IP ranges and localhost\n"
        "3. Disable HTTP redirects or validate redirect targets\n"
        "4. Use network segmentation for internal services"
    ),
    example_code="""
        // VULNERABLE
        String url = request.getParameter("url");
        RestTemplate rest = new RestTemplate();
        String result = rest.getForObject(url, String.class);

        // SECURE
        URL parsedUrl = new URL(url);
        if (!ALLOWED_HOSTS.contains(parsedUrl.getHost())) {
            throw new SecurityException("Host not allowed");
        }
        if (isPrivateIP(parsedUrl.getHost())) {
            throw new SecurityException("Private IP not allowed");
        }
    """,
    test_cases=[
        {"name": "RestTemplate with param URL", "method": "fetchUrl", "expected": True, "contains": ["getForObject"]}
    ]
)


HARDCODED_SECRETS_PATTERN = SecurityPattern(
    id="JAVA_SECRETS_001",
    name="Hardcoded Secrets",
    category=VulnerabilityCategory.AUTHENTICATION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Passwords, API keys, or cryptographic keys hardcoded in source code."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nl.id,
            nl.code,
            nl.filename,
            nl.line_number,
            'HARDCODED_SECRET' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_literal nl
        WHERE (nl.code LIKE '%password%' OR nl.code LIKE '%secret%'
               OR nl.code LIKE '%apiKey%' OR nl.code LIKE '%api_key%'
               OR nl.code LIKE '%token%' OR nl.code LIKE '%credential%')
          AND nl.code NOT LIKE '%placeholder%'
          AND nl.code NOT LIKE '%example%'
          AND nl.filename NOT LIKE '%Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-798"],
    remediation=(
        "1. Use environment variables or configuration files\n"
        "2. Use secrets management (HashiCorp Vault, AWS Secrets Manager)\n"
        "3. Use Spring Cloud Config with encryption\n"
        "4. Never commit secrets to version control"
    ),
    example_code="""
        // VULNERABLE
        private static final String API_KEY = "sk-1234567890abcdef";
        String password = "admin123";

        // SECURE
        String apiKey = System.getenv("API_KEY");
        @Value("${db.password}")
        private String password;
    """,
    test_cases=[
        {"name": "hardcoded password", "method": "connect", "expected": True, "contains": ["password"]}
    ]
)


# Aggregate all Java patterns
JAVA_PATTERNS: Dict[str, SecurityPattern] = {
    "JAVA_SQL_001": SQL_INJECTION_JAVA_PATTERN,
    "JAVA_JNDI_001": JNDI_INJECTION_PATTERN,
    "JAVA_DESER_001": DESERIALIZATION_PATTERN,
    "JAVA_XXE_001": XXE_PATTERN,
    "JAVA_PATH_001": PATH_TRAVERSAL_PATTERN,
    "JAVA_CMD_001": COMMAND_INJECTION_PATTERN,
    "JAVA_LDAP_001": LDAP_INJECTION_PATTERN,
    "JAVA_SSRF_001": SSRF_PATTERN,
    "JAVA_SECRETS_001": HARDCODED_SECRETS_PATTERN,
}
