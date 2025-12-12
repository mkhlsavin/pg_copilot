"""
PostgreSQL-specific hypothesis generation patterns.

This subpackage contains patterns and hypotheses specifically designed
for analyzing PostgreSQL source code, including pg_dump, libpq, and
server-side components.

Importing this module auto-registers the PostgreSQLPatternProvider
with the ProviderRegistry.
"""

# Auto-register the PostgreSQL provider
from .provider import PostgreSQLPatternProvider

from .patterns import (
    PG_DUMP_SINKS,
    PG_DUMP_SOURCES,
    PG_DUMP_SANITIZERS,
    PG_SPI_SINKS,
    PG_SPI_SOURCES,
    PG_SPI_SANITIZERS,
    PG_LIBPQ_SINKS,
    PG_LIBPQ_SOURCES,
    PG_LIBPQ_SANITIZERS,
    PG_ACL_FUNCTIONS,
    CVEPattern,
    POSTGRESQL_CVE_PATTERNS,
    get_pg_pattern_for_cve,
    get_all_pg_sinks,
    get_all_pg_sources,
    get_all_pg_sanitizers,
)

__all__ = [
    # Provider
    "PostgreSQLPatternProvider",
    # Pattern data
    "PG_DUMP_SINKS",
    "PG_DUMP_SOURCES",
    "PG_DUMP_SANITIZERS",
    "PG_SPI_SINKS",
    "PG_SPI_SOURCES",
    "PG_SPI_SANITIZERS",
    "PG_LIBPQ_SINKS",
    "PG_LIBPQ_SOURCES",
    "PG_LIBPQ_SANITIZERS",
    "PG_ACL_FUNCTIONS",
    "CVEPattern",
    "POSTGRESQL_CVE_PATTERNS",
    "get_pg_pattern_for_cve",
    "get_all_pg_sinks",
    "get_all_pg_sources",
    "get_all_pg_sanitizers",
]
