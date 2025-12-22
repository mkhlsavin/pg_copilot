"""PostgreSQL Default Prompt Templates.

Fallback prompt templates when YAML configuration is not available.
"""
from typing import Dict


def get_default_prompts() -> Dict[str, Dict[str, str]]:
    """
    Get fallback prompt templates if YAML not available.

    Returns:
        Dictionary mapping prompt type to system/user templates
    """
    return {
        "security_audit": {
            "system": (
                "You are a PostgreSQL security expert specializing in "
                "identifying vulnerabilities in database system source code. "
                "Focus on SQL injection, buffer overflows, privilege escalation, "
                "and memory safety issues specific to PostgreSQL's architecture."
            ),
            "user_template": (
                "Analyze the following PostgreSQL code for security vulnerabilities:\n\n"
                "{code}\n\n"
                "Consider PostgreSQL-specific attack vectors including:\n"
                "- SPI interface abuse\n"
                "- Extension loading attacks\n"
                "- COPY command injection\n"
                "- Privilege escalation via superuser functions"
            ),
        },
        "performance": {
            "system": (
                "You are a PostgreSQL performance expert with deep knowledge of "
                "query execution, memory management, and I/O optimization. "
                "Focus on identifying bottlenecks in the executor, planner, "
                "and storage subsystems."
            ),
            "user_template": (
                "Analyze the following PostgreSQL code for performance issues:\n\n"
                "{code}\n\n"
                "Consider:\n"
                "- Memory allocation patterns (palloc/pfree)\n"
                "- Lock contention\n"
                "- Buffer management\n"
                "- Query plan efficiency"
            ),
        },
        "onboarding": {
            "system": (
                "You are a PostgreSQL internals expert helping developers understand "
                "the codebase architecture. Explain concepts clearly with references "
                "to specific subsystems and their interactions."
            ),
            "user_template": (
                "Explain the following aspect of PostgreSQL:\n\n"
                "{query}\n\n"
                "Provide context about which subsystems are involved and "
                "how they interact. Reference specific functions where helpful."
            ),
        },
        "documentation": {
            "system": (
                "You are a PostgreSQL documentation expert. Generate clear, "
                "comprehensive documentation for PostgreSQL internal functions "
                "and modules following PostgreSQL's documentation style."
            ),
            "user_template": (
                "Generate documentation for:\n\n"
                "{code}\n\n"
                "Include:\n"
                "- Function purpose and behavior\n"
                "- Parameters and return values\n"
                "- Error conditions\n"
                "- Related functions"
            ),
        },
    }
