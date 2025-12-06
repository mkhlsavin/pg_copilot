"""
Cryptography Vulnerability Patterns

Patterns for detecting weak cryptography, improper certificate validation,
cleartext storage, and insufficient entropy issues.

CWE-327 (Broken Crypto), CWE-295 (Improper Cert), CWE-312 (Cleartext Storage),
CWE-330 (Insufficient Entropy)
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


WEAK_CRYPTO_PATTERN = SecurityPattern(
    id="CRYPTO_001",
    name="Weak Cryptographic Algorithm",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Use of weak or broken cryptographic algorithms (MD5, SHA1, DES) "
        "that don't provide adequate security."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.name AS weak_function,
            'WEAK_CRYPTOGRAPHY' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.name LIKE '%md5%'
            OR nc.name LIKE '%sha1%'
            OR nc.name LIKE '%des%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-327", "CWE-328"],
    remediation=(
        "1. Replace MD5 with SHA-256 or SHA-3\n"
        "2. Replace SHA1 with SHA-256 for signatures\n"
        "3. Replace DES with AES-256\n"
        "4. Use modern crypto libraries (OpenSSL 1.1+, libsodium)\n"
        "5. Follow NIST or OWASP cryptography guidelines"
    ),
    example_code="""
        // VULNERABLE
        unsigned char hash[16];
        MD5(password, strlen(password), hash);

        // SECURE
        unsigned char hash[32];
        SHA256(password, strlen(password), hash);
    """,
    test_cases=[
        {"name": "MD5 usage", "method": "hash_password", "expected": True, "contains": ["MD5"]}
    ]
)


IMPROPER_CERT_PATTERN = SecurityPattern(
    id="IMPROPER_CERT_001",
    name="Improper SSL/TLS Certificate Validation",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "SSL/TLS connections that skip or weaken certificate validation "
        "are vulnerable to man-in-the-middle attacks."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'IMPROPER_CERT_VALIDATION' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (nc.code LIKE '%VERIFY_NONE%'
            OR nc.code LIKE '%verify_mode%0%'
            OR nc.code LIKE '%SSL_CTX_set_verify%NULL%'
            OR nc.code LIKE '%verify%false%'
            OR nc.code LIKE '%check_hostname%False%'
            OR nc.code LIKE '%CURLOPT_SSL_VERIFYPEER%0%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-295"],
    remediation=(
        "1. Always verify SSL certificates\n"
        "2. Use system CA certificate bundle\n"
        "3. Enable hostname verification\n"
        "4. Pin certificates for critical services\n"
        "5. Keep certificate stores updated"
    ),
    example_code="""
        // VULNERABLE
        SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL);  // MITM risk

        // SECURE
        SSL_CTX_set_verify(ctx, SSL_VERIFY_PEER, verify_callback);
        SSL_CTX_load_verify_locations(ctx, "/etc/ssl/certs/ca-bundle.crt", NULL);
    """,
    test_cases=[
        {"name": "SSL verify disabled", "method": "create_ssl_connection", "expected": True, "contains": ["VERIFY_NONE"]}
    ]
)


CLEARTEXT_STORAGE_PATTERN = SecurityPattern(
    id="CLEARTEXT_STORAGE_001",
    name="Cleartext Storage of Sensitive Data",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Sensitive data stored without encryption can be exposed through "
        "file access, backups, or data breaches."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'CLEARTEXT_STORAGE' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('fwrite', 'write', 'fputs', 'fprintf', 'fputc',
                          'PQexec', 'SPI_execute', 'insert_row')
          AND (LOWER(nc.code) LIKE '%password%'
            OR LOWER(nc.code) LIKE '%secret%'
            OR LOWER(nc.code) LIKE '%api_key%'
            OR LOWER(nc.code) LIKE '%token%'
            OR LOWER(nc.code) LIKE '%credit_card%'
            OR LOWER(nc.code) LIKE '%ssn%')
          AND nc.code NOT LIKE '%encrypt%'
          AND nc.code NOT LIKE '%hash%'
          AND nc.code NOT LIKE '%crypt%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-312", "CWE-313"],
    remediation=(
        "1. Encrypt sensitive data before storage\n"
        "2. Use strong encryption (AES-256)\n"
        "3. Store encryption keys separately\n"
        "4. Hash passwords with bcrypt/argon2\n"
        "5. Implement key rotation"
    ),
    example_code="""
        // VULNERABLE
        fwrite(user_password, 1, strlen(user_password), file);  // Plaintext

        // SECURE
        char *hashed = bcrypt_hash(user_password);
        fwrite(hashed, 1, strlen(hashed), file);
    """,
    test_cases=[
        {"name": "password written plaintext", "method": "save_user_credentials", "expected": True, "contains": ["password", "write"]}
    ]
)


INSUFFICIENT_ENTROPY_PATTERN = SecurityPattern(
    id="INSUFFICIENT_ENTROPY_001",
    name="Insufficient Entropy for Security Tokens",
    category=VulnerabilityCategory.CRYPTOGRAPHY,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Security tokens generated with insufficient randomness can be "
        "predicted or brute-forced by attackers."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            SUBSTRING(nc.method_full_name, 1, POSITION(':' IN nc.method_full_name || ':') - 1) AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'INSUFFICIENT_ENTROPY' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE (LOWER(nc.code) LIKE '%token%'
            OR LOWER(nc.code) LIKE '%session%'
            OR LOWER(nc.code) LIKE '%nonce%'
            OR LOWER(nc.code) LIKE '%salt%')
          AND (nc.name IN ('rand', 'random', 'srand', 'rand_r')
               OR nc.code LIKE '%time(%'
               OR nc.code LIKE '%clock(%'
               OR nc.code LIKE '%getpid(%')
          AND nc.code NOT LIKE '%/dev/urandom%'
          AND nc.code NOT LIKE '%RAND_bytes%'
          AND nc.code NOT LIKE '%getrandom%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-330", "CWE-331", "CWE-338"],
    remediation=(
        "1. Use cryptographically secure PRNG (CSPRNG)\n"
        "2. Use /dev/urandom or getrandom() on Linux\n"
        "3. Use RAND_bytes() from OpenSSL\n"
        "4. Never seed with predictable values (time, PID)\n"
        "5. Use sufficient token length (128+ bits)"
    ),
    example_code="""
        // VULNERABLE
        srand(time(NULL));
        int token = rand();  // Predictable!

        // SECURE
        unsigned char token[32];
        RAND_bytes(token, sizeof(token));  // Crypto-secure
    """,
    test_cases=[
        {"name": "weak random for token", "method": "generate_session_token", "expected": True, "contains": ["rand", "token"]}
    ]
)


# Registry of crypto patterns
CRYPTO_PATTERNS: Dict[str, SecurityPattern] = {
    "WEAK_CRYPTO": WEAK_CRYPTO_PATTERN,
    "IMPROPER_CERT": IMPROPER_CERT_PATTERN,
    "CLEARTEXT_STORAGE": CLEARTEXT_STORAGE_PATTERN,
    "INSUFFICIENT_ENTROPY": INSUFFICIENT_ENTROPY_PATTERN,
}
