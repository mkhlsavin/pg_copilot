"""
Security Knowledge Base for Hypothesis Generation.

Contains CWE entries, CAPEC attack patterns, and language-specific
vulnerability patterns used for generating security hypotheses.
"""

from typing import Dict, List, Optional
from .models import CWEEntry, CAPECPattern, LanguagePattern, Severity


# =============================================================================
# CWE Database - Common Weakness Enumeration
# =============================================================================

CWE_DATABASE: Dict[str, CWEEntry] = {
    # Memory Safety (Critical for C/C++)
    "CWE-120": CWEEntry(
        id="CWE-120",
        name="Buffer Copy without Checking Size of Input",
        description="The program copies an input buffer to an output buffer without verifying that the size of the input buffer is less than the size of the output buffer, leading to a buffer overflow.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++"],
        prevalence=0.85,
        exploitability=0.90,
        related_cwes=["CWE-119", "CWE-787", "CWE-788"],
        capec_ids=["CAPEC-100", "CAPEC-123"],
        mitigations=["Use safe string functions (strlcpy, snprintf)", "Bounds checking"],
        detection_methods=["Static analysis", "Fuzzing", "Code review"],
    ),
    "CWE-119": CWEEntry(
        id="CWE-119",
        name="Improper Restriction of Operations within Memory Buffer",
        description="The software performs operations on a memory buffer, but it can read from or write to a memory location outside the intended boundary.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++"],
        prevalence=0.80,
        exploitability=0.85,
        related_cwes=["CWE-120", "CWE-787", "CWE-125"],
        capec_ids=["CAPEC-100"],
        mitigations=["Bounds checking", "Safe memory functions"],
    ),
    "CWE-787": CWEEntry(
        id="CWE-787",
        name="Out-of-bounds Write",
        description="The software writes data past the end, or before the beginning, of the intended buffer.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++"],
        prevalence=0.75,
        exploitability=0.90,
        related_cwes=["CWE-119", "CWE-120"],
        capec_ids=["CAPEC-100"],
    ),
    "CWE-125": CWEEntry(
        id="CWE-125",
        name="Out-of-bounds Read",
        description="The software reads data past the end, or before the beginning, of the intended buffer.",
        severity=Severity.HIGH,
        cvss_base=7.5,
        languages=["C", "C++"],
        prevalence=0.70,
        exploitability=0.75,
        related_cwes=["CWE-119", "CWE-126"],
        capec_ids=["CAPEC-540"],
    ),
    "CWE-416": CWEEntry(
        id="CWE-416",
        name="Use After Free",
        description="Referencing memory after it has been freed can cause a program to crash, use unexpected values, or execute code.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++"],
        prevalence=0.75,
        exploitability=0.80,
        related_cwes=["CWE-415", "CWE-825"],
        capec_ids=["CAPEC-130"],
        mitigations=["Set pointers to NULL after free", "Smart pointers"],
    ),
    "CWE-415": CWEEntry(
        id="CWE-415",
        name="Double Free",
        description="The product calls free() twice on the same memory address, potentially leading to modification of unexpected memory locations.",
        severity=Severity.HIGH,
        cvss_base=7.5,
        languages=["C", "C++"],
        prevalence=0.60,
        exploitability=0.70,
        related_cwes=["CWE-416"],
        capec_ids=["CAPEC-130"],
    ),
    "CWE-476": CWEEntry(
        id="CWE-476",
        name="NULL Pointer Dereference",
        description="A NULL pointer dereference occurs when the application dereferences a pointer that it expects to be valid, but is NULL.",
        severity=Severity.MEDIUM,
        cvss_base=5.5,
        languages=["C", "C++"],
        prevalence=0.80,
        exploitability=0.60,
        related_cwes=["CWE-252", "CWE-690"],
        capec_ids=["CAPEC-129"],
        mitigations=["NULL checks before dereference"],
    ),
    "CWE-190": CWEEntry(
        id="CWE-190",
        name="Integer Overflow or Wraparound",
        description="The software performs a calculation that can produce an integer overflow or wraparound, when the logic assumes that the resulting value will always be larger than the original value.",
        severity=Severity.HIGH,
        cvss_base=8.1,
        languages=["C", "C++", "Java"],
        prevalence=0.70,
        exploitability=0.75,
        related_cwes=["CWE-191", "CWE-680"],
        capec_ids=["CAPEC-92"],
        mitigations=["Safe integer operations", "Overflow checks"],
    ),
    "CWE-191": CWEEntry(
        id="CWE-191",
        name="Integer Underflow",
        description="The product subtracts one value from another, such that the result is less than the minimum allowable integer value, which produces a value that is not equal to the correct result.",
        severity=Severity.HIGH,
        cvss_base=7.5,
        languages=["C", "C++"],
        prevalence=0.55,
        exploitability=0.65,
        related_cwes=["CWE-190"],
        capec_ids=["CAPEC-92"],
    ),

    # Injection Vulnerabilities
    "CWE-78": CWEEntry(
        id="CWE-78",
        name="OS Command Injection",
        description="The software constructs all or part of an OS command using externally-influenced input, but does not neutralize or incorrectly neutralizes special elements.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++", "Python", "Java", "PHP"],
        prevalence=0.65,
        exploitability=0.95,
        related_cwes=["CWE-77", "CWE-88"],
        capec_ids=["CAPEC-88", "CAPEC-108"],
        mitigations=["Input validation", "Parameterized commands", "Avoid shell execution"],
    ),
    "CWE-89": CWEEntry(
        id="CWE-89",
        name="SQL Injection",
        description="The software constructs all or part of an SQL command using externally-influenced input, but does not neutralize or incorrectly neutralizes special elements.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++", "Python", "Java", "PHP"],
        prevalence=0.60,
        exploitability=0.95,
        related_cwes=["CWE-564", "CWE-943"],
        capec_ids=["CAPEC-66", "CAPEC-108"],
        mitigations=["Parameterized queries", "Input validation", "quote_literal/quote_identifier"],
    ),
    "CWE-94": CWEEntry(
        id="CWE-94",
        name="Improper Control of Generation of Code ('Code Injection')",
        description="The software constructs all or part of a code segment using externally-influenced input, but does not neutralize or incorrectly neutralizes special elements.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++", "Python", "Java", "PHP"],
        prevalence=0.50,
        exploitability=0.90,
        related_cwes=["CWE-95", "CWE-96"],
        capec_ids=["CAPEC-242", "CAPEC-35"],
        mitigations=["Input validation", "Sandboxing", "Safe APIs"],
    ),
    "CWE-134": CWEEntry(
        id="CWE-134",
        name="Use of Externally-Controlled Format String",
        description="The software uses a function that accepts a format string as an argument, but the format string originates from an external source.",
        severity=Severity.CRITICAL,
        cvss_base=9.8,
        languages=["C", "C++"],
        prevalence=0.45,
        exploitability=0.85,
        related_cwes=["CWE-20"],
        capec_ids=["CAPEC-135"],
        mitigations=["Never pass user input as format string", "Use fixed format strings"],
    ),

    # Information Disclosure
    "CWE-200": CWEEntry(
        id="CWE-200",
        name="Exposure of Sensitive Information to an Unauthorized Actor",
        description="The product exposes sensitive information to an actor that is not explicitly authorized to have access to that information.",
        severity=Severity.MEDIUM,
        cvss_base=5.3,
        languages=["C", "C++", "Python", "Java"],
        prevalence=0.55,
        exploitability=0.70,
        related_cwes=["CWE-201", "CWE-209"],
        capec_ids=["CAPEC-118", "CAPEC-169"],
        mitigations=["Access control checks", "Data masking"],
    ),
    "CWE-209": CWEEntry(
        id="CWE-209",
        name="Generation of Error Message Containing Sensitive Information",
        description="The software generates an error message that includes sensitive information about its environment, users, or associated data.",
        severity=Severity.MEDIUM,
        cvss_base=4.3,
        languages=["C", "C++", "Python", "Java"],
        prevalence=0.50,
        exploitability=0.60,
        related_cwes=["CWE-200"],
        capec_ids=["CAPEC-118"],
    ),

    # Access Control
    "CWE-284": CWEEntry(
        id="CWE-284",
        name="Improper Access Control",
        description="The software does not restrict or incorrectly restricts access to a resource from an unauthorized actor.",
        severity=Severity.HIGH,
        cvss_base=7.5,
        languages=["C", "C++", "Python", "Java"],
        prevalence=0.60,
        exploitability=0.75,
        related_cwes=["CWE-285", "CWE-862"],
        capec_ids=["CAPEC-1", "CAPEC-122"],
        mitigations=["Proper ACL checks", "Role-based access control"],
    ),
    "CWE-862": CWEEntry(
        id="CWE-862",
        name="Missing Authorization",
        description="The software does not perform an authorization check when an actor attempts to access a resource or perform an action.",
        severity=Severity.HIGH,
        cvss_base=7.5,
        languages=["C", "C++", "Python", "Java"],
        prevalence=0.55,
        exploitability=0.80,
        related_cwes=["CWE-284", "CWE-285"],
        capec_ids=["CAPEC-1"],
    ),

    # Cryptographic Issues
    "CWE-327": CWEEntry(
        id="CWE-327",
        name="Use of a Broken or Risky Cryptographic Algorithm",
        description="The use of a broken or risky cryptographic algorithm is an unnecessary risk that may result in the exposure of sensitive information.",
        severity=Severity.HIGH,
        cvss_base=7.5,
        languages=["C", "C++", "Python", "Java"],
        prevalence=0.40,
        exploitability=0.60,
        related_cwes=["CWE-328", "CWE-326"],
        capec_ids=["CAPEC-97"],
        mitigations=["Use modern cryptographic algorithms", "Follow NIST guidelines"],
    ),

    # Race Conditions
    "CWE-362": CWEEntry(
        id="CWE-362",
        name="Concurrent Execution using Shared Resource with Improper Synchronization ('Race Condition')",
        description="The program contains a code sequence that can run concurrently with other code, and the code sequence requires temporary, exclusive access to a shared resource.",
        severity=Severity.HIGH,
        cvss_base=7.0,
        languages=["C", "C++", "Java"],
        prevalence=0.45,
        exploitability=0.55,
        related_cwes=["CWE-367", "CWE-366"],
        capec_ids=["CAPEC-26", "CAPEC-29"],
        mitigations=["Proper locking", "Atomic operations"],
    ),
    "CWE-367": CWEEntry(
        id="CWE-367",
        name="Time-of-check Time-of-use (TOCTOU) Race Condition",
        description="The software checks the state of a resource before using that resource, but the resource's state can change between the check and the use.",
        severity=Severity.HIGH,
        cvss_base=7.0,
        languages=["C", "C++"],
        prevalence=0.40,
        exploitability=0.50,
        related_cwes=["CWE-362"],
        capec_ids=["CAPEC-27"],
    ),
}


# =============================================================================
# CAPEC Database - Attack Patterns
# =============================================================================

CAPEC_DATABASE: Dict[str, CAPECPattern] = {
    "CAPEC-100": CAPECPattern(
        id="CAPEC-100",
        name="Overflow Buffers",
        description="An adversary exploits a buffer overflow vulnerability by overwriting stack or heap memory.",
        related_cwes=["CWE-120", "CWE-119", "CWE-787"],
        attack_steps=[
            "Identify input that is copied to a buffer",
            "Determine buffer size and overflow potential",
            "Craft input that exceeds buffer size",
            "Overwrite return address or function pointer",
            "Redirect execution to malicious code",
        ],
        prerequisites=["Target must use unsafe buffer operations", "Input reaches buffer copy"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.8,
        skill_level="Medium",
    ),
    "CAPEC-88": CAPECPattern(
        id="CAPEC-88",
        name="OS Command Injection",
        description="An adversary modifies inputs used to construct system commands to execute arbitrary commands.",
        related_cwes=["CWE-78", "CWE-77"],
        attack_steps=[
            "Identify user input passed to system commands",
            "Test for shell metacharacter processing",
            "Inject shell metacharacters (;, |, &&, etc.)",
            "Execute arbitrary commands",
        ],
        prerequisites=["User input reaches command execution"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.9,
        skill_level="Low",
    ),
    "CAPEC-66": CAPECPattern(
        id="CAPEC-66",
        name="SQL Injection",
        description="An adversary exploits improper input validation to run SQL queries in the database.",
        related_cwes=["CWE-89"],
        attack_steps=[
            "Identify user input in SQL queries",
            "Test for SQL injection (single quote, OR 1=1)",
            "Extract database schema",
            "Extract sensitive data or modify data",
        ],
        prerequisites=["Dynamic SQL query construction"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.9,
        skill_level="Low",
    ),
    "CAPEC-135": CAPECPattern(
        id="CAPEC-135",
        name="Format String Injection",
        description="An adversary exploits format string vulnerabilities to read/write memory.",
        related_cwes=["CWE-134"],
        attack_steps=[
            "Identify user input used as format string",
            "Use %x to read stack memory",
            "Use %n to write to memory",
            "Achieve code execution via GOT overwrite",
        ],
        prerequisites=["User input used as format string argument"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.7,
        skill_level="High",
    ),
    "CAPEC-130": CAPECPattern(
        id="CAPEC-130",
        name="Excessive Allocation",
        description="An adversary causes the application to allocate excessive resources.",
        related_cwes=["CWE-416", "CWE-415"],
        attack_steps=[
            "Trigger memory allocation",
            "Cause free of allocated memory",
            "Trigger reuse of freed memory",
            "Control freed memory contents",
        ],
        prerequisites=["Complex memory management"],
        typical_severity=Severity.HIGH,
        likelihood=0.6,
        skill_level="High",
    ),
    "CAPEC-92": CAPECPattern(
        id="CAPEC-92",
        name="Forced Integer Overflow",
        description="An adversary provides input that causes integer overflow in size calculations.",
        related_cwes=["CWE-190", "CWE-191"],
        attack_steps=[
            "Identify integer used in size calculations",
            "Determine maximum value boundaries",
            "Provide input causing wraparound",
            "Exploit resulting undersized allocation",
        ],
        prerequisites=["Integer used in allocation size"],
        typical_severity=Severity.HIGH,
        likelihood=0.7,
        skill_level="Medium",
    ),
    "CAPEC-242": CAPECPattern(
        id="CAPEC-242",
        name="Code Injection",
        description="An adversary inserts code into a program for execution.",
        related_cwes=["CWE-94", "CWE-95"],
        attack_steps=[
            "Identify code generation from input",
            "Craft malicious code payload",
            "Inject payload through input",
            "Achieve code execution",
        ],
        prerequisites=["Dynamic code generation from input"],
        typical_severity=Severity.CRITICAL,
        likelihood=0.8,
        skill_level="Medium",
    ),
    "CAPEC-118": CAPECPattern(
        id="CAPEC-118",
        name="Collect and Analyze Information",
        description="An adversary collects information about the target through various means.",
        related_cwes=["CWE-200", "CWE-209"],
        attack_steps=[
            "Trigger error conditions",
            "Collect error messages and stack traces",
            "Analyze system behavior",
            "Use information for further attacks",
        ],
        prerequisites=["Verbose error messages enabled"],
        typical_severity=Severity.MEDIUM,
        likelihood=0.8,
        skill_level="Low",
    ),
}


# =============================================================================
# Language-Specific Patterns
# =============================================================================

C_DANGEROUS_SINKS: Dict[str, List[str]] = {
    "memory": [
        "strcpy", "strcat", "sprintf", "gets", "memcpy", "memmove",
        "strncpy", "strncat",  # Still dangerous if size wrong
        "wcscpy", "wcscat",   # Wide char versions
    ],
    "format": [
        "printf", "fprintf", "sprintf", "snprintf", "vprintf",
        "vfprintf", "vsprintf", "vsnprintf", "syslog",
    ],
    "command": [
        "system", "popen", "execl", "execle", "execlp",
        "execv", "execve", "execvp", "execvpe",
    ],
    "file": [
        "fopen", "open", "read", "write", "fread", "fwrite",
    ],
    "memory_alloc": [
        "malloc", "calloc", "realloc", "free",
        # PostgreSQL-specific (palloc, pfree) moved to postgresql/provider.py
    ],
}

C_TAINT_SOURCES: Dict[str, List[str]] = {
    "network": [
        "recv", "recvfrom", "recvmsg", "read",
    ],
    "file": [
        "fread", "fscanf", "fgets", "getline",
    ],
    "user_input": [
        "getenv", "argv",
    ],
    # PostgreSQL-specific sources (PQgetvalue, SPI_getvalue, etc.)
    # moved to postgresql/provider.py
}

C_SANITIZERS: Dict[str, List[str]] = {
    "bounds_check": [
        "sizeof", "strlen", "strnlen",
    ],
    "safe_string": [
        "strlcpy", "strlcat", "snprintf", "vsnprintf",
        # PostgreSQL-specific (pstrdup) moved to postgresql/provider.py
    ],
    "escaping": [
        # Generic C escaping - project-specific (fmtId, PQescapeIdentifier, etc.)
        # moved to providers
    ],
    "null_check": [
        "!= NULL", "== NULL", "if (ptr)",
    ],
    # PostgreSQL ACL functions moved to postgresql/provider.py
}

# Combine into LanguagePattern objects
C_LANGUAGE_PATTERNS: List[LanguagePattern] = [
    LanguagePattern(
        language="C",
        category="buffer_overflow",
        sinks=C_DANGEROUS_SINKS["memory"],
        sources=C_TAINT_SOURCES["network"] + C_TAINT_SOURCES["file"] + C_TAINT_SOURCES["user_input"],
        sanitizers=C_SANITIZERS["bounds_check"] + C_SANITIZERS["safe_string"],
        related_cwes=["CWE-120", "CWE-119", "CWE-787"],
        description="Buffer overflow via unsafe memory copy functions",
    ),
    LanguagePattern(
        language="C",
        category="format_string",
        sinks=C_DANGEROUS_SINKS["format"],
        sources=C_TAINT_SOURCES["network"] + C_TAINT_SOURCES["file"] + C_TAINT_SOURCES["user_input"],
        sanitizers=[],  # No sanitizer - format string must be literal
        related_cwes=["CWE-134"],
        description="Format string vulnerability via user-controlled format",
    ),
    LanguagePattern(
        language="C",
        category="command_injection",
        sinks=C_DANGEROUS_SINKS["command"],
        sources=C_TAINT_SOURCES["user_input"],  # Database sources from providers
        sanitizers=C_SANITIZERS["escaping"],
        related_cwes=["CWE-78"],
        description="OS command injection via shell execution",
    ),
    LanguagePattern(
        language="C",
        category="use_after_free",
        sinks=["*"],  # Any use after free
        sources=C_DANGEROUS_SINKS["memory_alloc"],
        sanitizers=["= NULL"],
        related_cwes=["CWE-416", "CWE-415"],
        description="Use of memory after it has been freed",
    ),
    LanguagePattern(
        language="C",
        category="integer_overflow",
        sinks=C_DANGEROUS_SINKS["memory_alloc"],
        sources=C_TAINT_SOURCES["network"],  # Database sources from providers
        sanitizers=["overflow", "> MAX", "< 0"],
        related_cwes=["CWE-190", "CWE-191"],
        description="Integer overflow in size calculations",
    ),
]

# PostgreSQL-specific patterns moved to postgresql/provider.py


# =============================================================================
# Knowledge Base Class
# =============================================================================

class SecurityKnowledgeBase:
    """Security knowledge base for hypothesis generation.

    Provides access to CWE, CAPEC, and language-specific vulnerability patterns.
    Supports plugin-based extension via PatternProvider interface.

    Args:
        providers: List of provider names to load (e.g., ["postgresql"]).
                   If None, loads all registered providers.
    """

    def __init__(self, providers: Optional[List[str]] = None):
        self.cwe_db = CWE_DATABASE
        self.capec_db = CAPEC_DATABASE

        # Start with universal C language patterns
        self.c_patterns = list(C_LANGUAGE_PATTERNS)

        # Load patterns from providers
        self._load_providers(providers)

    def _load_providers(self, provider_names: Optional[List[str]] = None) -> None:
        """Load patterns from registered providers.

        Args:
            provider_names: Specific providers to load, or None for all.
        """
        from .providers.registry import ProviderRegistry

        if provider_names is None:
            # Load all registered providers
            providers = ProviderRegistry.all()
        else:
            # Load specific providers
            providers = []
            for name in provider_names:
                provider = ProviderRegistry.get(name)
                if provider:
                    providers.append(provider)

        # Extend patterns from each provider
        for provider in providers:
            self.c_patterns.extend(provider.get_language_patterns())

    # CWE Access Methods
    def get_cwe(self, cwe_id: str) -> Optional[CWEEntry]:
        """Get CWE entry by ID."""
        return self.cwe_db.get(cwe_id)

    def get_cwes_by_severity(self, severity: Severity) -> List[CWEEntry]:
        """Get all CWEs with specified severity."""
        return [cwe for cwe in self.cwe_db.values() if cwe.severity == severity]

    def get_cwes_by_language(self, language: str) -> List[CWEEntry]:
        """Get all CWEs applicable to a language."""
        return [cwe for cwe in self.cwe_db.values() if language in cwe.languages]

    def get_top_cwes(self, language: str, n: int = 10) -> List[CWEEntry]:
        """Get top N CWEs by risk score for a language."""
        cwes = self.get_cwes_by_language(language)
        return sorted(cwes, key=lambda c: c.risk_score, reverse=True)[:n]

    # CAPEC Access Methods
    def get_capec(self, capec_id: str) -> Optional[CAPECPattern]:
        """Get CAPEC pattern by ID."""
        return self.capec_db.get(capec_id)

    def get_capecs_for_cwe(self, cwe_id: str) -> List[CAPECPattern]:
        """Get attack patterns that exploit a specific CWE."""
        return [capec for capec in self.capec_db.values() if cwe_id in capec.related_cwes]

    # Language Pattern Access
    def get_patterns_by_language(self, language: str) -> List[LanguagePattern]:
        """Get vulnerability patterns for a language."""
        return [p for p in self.c_patterns if p.language == language]

    def get_patterns_by_category(self, category: str) -> List[LanguagePattern]:
        """Get vulnerability patterns by category."""
        return [p for p in self.c_patterns if p.category == category]

    def get_sinks_for_category(self, category: str) -> List[str]:
        """Get sink functions for a vulnerability category."""
        patterns = self.get_patterns_by_category(category)
        sinks = []
        for p in patterns:
            sinks.extend(p.sinks)
        return list(set(sinks))

    def get_sources_for_category(self, category: str) -> List[str]:
        """Get source functions for a vulnerability category."""
        patterns = self.get_patterns_by_category(category)
        sources = []
        for p in patterns:
            sources.extend(p.sources)
        return list(set(sources))

    def get_sanitizers_for_category(self, category: str) -> List[str]:
        """Get sanitizer functions for a vulnerability category."""
        patterns = self.get_patterns_by_category(category)
        sanitizers = []
        for p in patterns:
            sanitizers.extend(p.sanitizers)
        return list(set(sanitizers))

    # Statistics
    def get_stats(self) -> Dict[str, int]:
        """Get knowledge base statistics."""
        return {
            "total_cwes": len(self.cwe_db),
            "total_capecs": len(self.capec_db),
            "total_patterns": len(self.c_patterns),
            "critical_cwes": len(self.get_cwes_by_severity(Severity.CRITICAL)),
            "high_cwes": len(self.get_cwes_by_severity(Severity.HIGH)),
            "c_patterns": len([p for p in self.c_patterns if p.language == "C"]),
        }


# Singleton instance
_kb_instance: Optional[SecurityKnowledgeBase] = None


def get_knowledge_base() -> SecurityKnowledgeBase:
    """Get singleton knowledge base instance."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = SecurityKnowledgeBase()
    return _kb_instance
