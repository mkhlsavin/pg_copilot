"""
C# Security Patterns

Patterns for detecting vulnerabilities specific to C# and .NET:
- SQL injection in ADO.NET/Entity Framework
- XSS in ASP.NET
- Insecure deserialization (BinaryFormatter)
- Path traversal
- LDAP injection
- XXE in XML processing

CWE-78, CWE-89, CWE-79, CWE-502, CWE-22, CWE-611
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


SQL_INJECTION_CSHARP_PATTERN = SecurityPattern(
    id="CS_SQL_001",
    name="SQL Injection in ADO.NET",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL injection via string concatenation in SqlCommand or DbCommand. "
        "Use parameterized queries with SqlParameter."
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
        WHERE nc.name IN ('SqlCommand', 'ExecuteReader', 'ExecuteNonQuery',
                          'ExecuteScalar', 'FromSqlRaw', 'ExecuteSqlRaw')
          AND (nc.code LIKE '%+%' OR nc.code LIKE '%$%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use parameterized queries with SqlParameter\n"
        "2. Use Entity Framework LINQ queries\n"
        "3. Use FromSqlInterpolated instead of FromSqlRaw\n"
        "4. Validate and sanitize input"
    ),
    example_code="""
        // VULNERABLE
        var cmd = new SqlCommand($"SELECT * FROM Users WHERE Id = {id}", conn);
        context.Users.FromSqlRaw("SELECT * FROM Users WHERE Name = '" + name + "'");

        // SECURE
        var cmd = new SqlCommand("SELECT * FROM Users WHERE Id = @id", conn);
        cmd.Parameters.AddWithValue("@id", id);

        context.Users.FromSqlInterpolated($"SELECT * FROM Users WHERE Id = {id}");
    """,
    test_cases=[
        {"name": "SqlCommand with concat", "method": "GetUser", "expected": True, "contains": ["SqlCommand", "+"]}
    ]
)


XSS_ASPNET_PATTERN = SecurityPattern(
    id="CS_XSS_001",
    name="XSS in ASP.NET",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Cross-site scripting via Html.Raw(), WriteLiteral, or disabled "
        "request validation in ASP.NET MVC/Core."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'XSS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('Raw', 'WriteLiteral', 'HtmlString')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-79"],
    remediation=(
        "1. Avoid Html.Raw() with user input\n"
        "2. Use automatic Razor encoding (@Model.Value)\n"
        "3. Use AntiXSS library for encoding\n"
        "4. Implement Content Security Policy"
    ),
    example_code="""
        // VULNERABLE
        @Html.Raw(Model.UserContent)
        Response.Write(userInput);

        // SECURE
        @Model.UserContent  // Automatically encoded
        @Html.Encode(Model.UserContent)
    """,
    test_cases=[
        {"name": "Html.Raw with user data", "method": "RenderContent", "expected": True, "contains": ["Raw"]}
    ]
)


DESERIALIZATION_CSHARP_PATTERN = SecurityPattern(
    id="CS_DESER_001",
    name="Insecure Deserialization (BinaryFormatter)",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "BinaryFormatter, NetDataContractSerializer, SoapFormatter, and similar "
        "deserializers can execute arbitrary code when deserializing untrusted data."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSECURE_DESERIALIZATION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('Deserialize', 'UnsafeDeserialize', 'ReadObject')
          AND (nc.code LIKE '%BinaryFormatter%'
               OR nc.code LIKE '%NetDataContractSerializer%'
               OR nc.code LIKE '%SoapFormatter%'
               OR nc.code LIKE '%LosFormatter%'
               OR nc.code LIKE '%ObjectStateFormatter%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-502"],
    remediation=(
        "1. Use JSON.NET or System.Text.Json instead\n"
        "2. Never deserialize untrusted data with BinaryFormatter\n"
        "3. Use DataContractSerializer with known types only\n"
        "4. BinaryFormatter is obsolete in .NET 5+"
    ),
    example_code="""
        // VULNERABLE
        var formatter = new BinaryFormatter();
        var obj = formatter.Deserialize(untrustedStream);

        // SECURE
        var options = new JsonSerializerOptions { ... };
        var obj = JsonSerializer.Deserialize<MyType>(json, options);
    """,
    test_cases=[
        {"name": "BinaryFormatter deserialize", "method": "LoadState", "expected": True, "contains": ["BinaryFormatter"]}
    ]
)


PATH_TRAVERSAL_CSHARP_PATTERN = SecurityPattern(
    id="CS_PATH_001",
    name="Path Traversal in File Operations",
    category=VulnerabilityCategory.INPUT_VALIDATION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Path traversal via user input in File.ReadAllText, FileStream, "
        "or other file operations without proper validation."
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
        WHERE nc.name IN ('ReadAllText', 'ReadAllBytes', 'WriteAllText',
                          'WriteAllBytes', 'Open', 'OpenRead', 'OpenWrite',
                          'FileStream', 'StreamReader', 'StreamWriter')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-22"],
    remediation=(
        "1. Use Path.GetFullPath and verify base directory\n"
        "2. Check Path.GetFileName for directory separators\n"
        "3. Use Path.Combine safely with validation\n"
        "4. Implement file access whitelist"
    ),
    example_code="""
        // VULNERABLE
        var content = File.ReadAllText(Path.Combine(baseDir, userInput));

        // SECURE
        var fullPath = Path.GetFullPath(Path.Combine(baseDir, userInput));
        if (!fullPath.StartsWith(Path.GetFullPath(baseDir)))
            throw new UnauthorizedAccessException();
        var content = File.ReadAllText(fullPath);
    """,
    test_cases=[
        {"name": "File read with user path", "method": "GetFile", "expected": True, "contains": ["ReadAllText"]}
    ]
)


XXE_CSHARP_PATTERN = SecurityPattern(
    id="CS_XXE_001",
    name="XXE in XML Processing",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "XML External Entity injection when XmlReader or XmlDocument processes "
        "XML with DTD processing enabled."
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
        WHERE nc.name IN ('Load', 'LoadXml', 'Parse', 'Read')
          AND (nc.code LIKE '%XmlDocument%'
               OR nc.code LIKE '%XmlReader%'
               OR nc.code LIKE '%XmlTextReader%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-611"],
    remediation=(
        "1. Disable DTD processing: DtdProcessing.Prohibit\n"
        "2. Use XmlReader with secure settings\n"
        "3. Use XDocument (LINQ to XML) with safe settings\n"
        "4. Validate XML schema before processing"
    ),
    example_code="""
        // VULNERABLE
        var doc = new XmlDocument();
        doc.LoadXml(untrustedXml);

        // SECURE
        var settings = new XmlReaderSettings {
            DtdProcessing = DtdProcessing.Prohibit,
            XmlResolver = null
        };
        using var reader = XmlReader.Create(stream, settings);
    """,
    test_cases=[
        {"name": "XmlDocument load", "method": "ParseXml", "expected": True, "contains": ["XmlDocument", "Load"]}
    ]
)


LDAP_INJECTION_PATTERN = SecurityPattern(
    id="CS_LDAP_001",
    name="LDAP Injection",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "LDAP injection when user input is concatenated into LDAP search filters "
        "without proper escaping."
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
        WHERE nc.name IN ('FindAll', 'FindOne', 'DirectorySearcher')
          AND (nc.code LIKE '%Filter%' AND nc.code LIKE '%+%')
          AND nc.method_full_name NOT LIKE 'Test%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-90"],
    remediation=(
        "1. Use parameterized LDAP queries if available\n"
        "2. Escape special characters: *, (, ), \\, NUL\n"
        "3. Validate input against whitelist\n"
        "4. Use DirectoryServices.AccountManagement for AD"
    ),
    example_code="""
        // VULNERABLE
        searcher.Filter = $"(uid={username})";

        // SECURE
        var escapedUser = username.Replace("\\\\", "\\\\5c")
                                  .Replace("*", "\\\\2a");
        searcher.Filter = $"(uid={escapedUser})";
    """,
    test_cases=[
        {"name": "LDAP filter with concat", "method": "FindUser", "expected": True, "contains": ["Filter", "+"]}
    ]
)


# Registry of C# patterns
CSHARP_PATTERNS: Dict[str, SecurityPattern] = {
    "SQL_INJECTION": SQL_INJECTION_CSHARP_PATTERN,
    "XSS": XSS_ASPNET_PATTERN,
    "INSECURE_DESERIALIZATION": DESERIALIZATION_CSHARP_PATTERN,
    "PATH_TRAVERSAL": PATH_TRAVERSAL_CSHARP_PATTERN,
    "XXE": XXE_CSHARP_PATTERN,
    "LDAP_INJECTION": LDAP_INJECTION_PATTERN,
}
