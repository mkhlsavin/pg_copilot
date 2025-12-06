"""
Tag Export Module for CPG Enrichment

Provides standardized functions for exporting semantic tags from Joern CPG to DuckDB.
Tags provide rich semantic annotations for methods, including:
- Subsystem classification (code organization)
- Security risk levels
- Performance hotspots
- Cyclomatic complexity
- Function purpose descriptions

Author: CPG Integration - Phase P1
Date: December 2025
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Tag Category Definitions
# =============================================================================

TAG_CATEGORIES = {
    "subsystem-name": {
        "description": "Code organization/module classification",
        "example_values": ["executor", "parser", "storage", "network"],
        "joern_query": 'cpg.method.tag.name("subsystem.*")',
        "export_priority": 1
    },
    "security-risk": {
        "description": "Security risk level classification",
        "example_values": ["high", "medium", "low", "critical"],
        "joern_query": 'cpg.method.tag.name("security-risk")',
        "export_priority": 1
    },
    "taint-source": {
        "description": "Taint analysis source markers",
        "example_values": ["user-input", "network", "file", "env"],
        "joern_query": 'cpg.method.tag.name("taint-source")',
        "export_priority": 1
    },
    "taint-sink": {
        "description": "Taint analysis sink markers",
        "example_values": ["sql-query", "command-exec", "file-write"],
        "joern_query": 'cpg.method.tag.name("taint-sink")',
        "export_priority": 1
    },
    "perf-hotspot": {
        "description": "Performance critical code markers",
        "example_values": ["true", "false", "critical", "moderate"],
        "joern_query": 'cpg.method.tag.name("perf-hotspot")',
        "export_priority": 2
    },
    "cyclomatic-complexity": {
        "description": "Cyclomatic complexity metric",
        "example_values": ["1", "5", "10", "25"],
        "joern_query": 'cpg.method.tag.name("cyclomatic-complexity")',
        "export_priority": 2
    },
    "function-purpose": {
        "description": "LLM-enriched semantic description",
        "example_values": ["memory allocation", "error handling", "data validation"],
        "joern_query": 'cpg.method.tag.name("function-purpose")',
        "export_priority": 3
    },
    "api-category": {
        "description": "API categorization for public interfaces",
        "example_values": ["public", "internal", "deprecated", "experimental"],
        "joern_query": 'cpg.method.tag.name("api-category")',
        "export_priority": 2
    }
}


# =============================================================================
# Tag Export Functions
# =============================================================================

class TagExporter:
    """
    Handles export of semantic tags from Joern CPG to DuckDB.

    Usage:
        exporter = TagExporter(joern_client, duckdb_conn)
        exporter.export_all_tags()
    """

    def __init__(self, joern_client, duckdb_conn):
        """
        Initialize tag exporter.

        Args:
            joern_client: JoernClient instance for executing Scala queries
            duckdb_conn: DuckDB connection for inserting tags
        """
        self.joern_client = joern_client
        self.conn = duckdb_conn
        self.stats = {
            "tags_exported": 0,
            "edges_exported": 0,
            "categories": {}
        }

    def export_all_tags(self, categories: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Export all tags from Joern to DuckDB.

        Args:
            categories: Optional list of tag categories to export.
                       If None, exports all categories.

        Returns:
            Dict with export statistics per category
        """
        if categories is None:
            categories = list(TAG_CATEGORIES.keys())

        logger.info(f"Starting tag export for {len(categories)} categories")

        for category in categories:
            if category not in TAG_CATEGORIES:
                logger.warning(f"Unknown tag category: {category}")
                continue

            count = self._export_category(category)
            self.stats["categories"][category] = count
            self.stats["tags_exported"] += count

        logger.info(f"Tag export complete: {self.stats['tags_exported']} tags")
        return self.stats

    def _export_category(self, category: str) -> int:
        """
        Export a single tag category.

        Args:
            category: Tag category name

        Returns:
            Number of tags exported
        """
        logger.info(f"Exporting tag category: {category}")

        # Query to get all tags with their method associations
        query = f"""
        cpg.tag.filter(_.name.startsWith("{category}")).map {{ t =>
            Map(
                "id" -> t.id,
                "name" -> t.name,
                "value" -> t.value
            )
        }}.l
        """

        try:
            results = self.joern_client.execute_query(query)

            if not results:
                logger.info(f"No tags found for category: {category}")
                return 0

            # Batch insert tags
            tags_data = []
            for tag in results:
                tags_data.append((
                    tag.get("id"),
                    tag.get("name"),
                    tag.get("value")
                ))

            if tags_data:
                self.conn.executemany("""
                    INSERT OR IGNORE INTO nodes_tag (id, name, value)
                    VALUES (?, ?, ?)
                """, tags_data)

            logger.info(f"Exported {len(tags_data)} tags for category: {category}")
            return len(tags_data)

        except Exception as e:
            logger.error(f"Error exporting category {category}: {e}")
            return 0

    def export_tagged_by_edges(self) -> int:
        """
        Export TAGGED_BY edges connecting methods to their tags.

        Returns:
            Number of edges exported
        """
        logger.info("Exporting TAGGED_BY edges...")

        query = """
        cpg.method.flatMap { m =>
            m.tag.map { t =>
                Map("src" -> m.id, "dst" -> t.id)
            }
        }.l
        """

        try:
            results = self.joern_client.execute_query(query)

            if not results:
                logger.info("No TAGGED_BY edges found")
                return 0

            edges_data = [(e.get("src"), e.get("dst")) for e in results]

            if edges_data:
                self.conn.executemany("""
                    INSERT OR IGNORE INTO edges_tagged_by (src, dst)
                    VALUES (?, ?)
                """, edges_data)

            self.stats["edges_exported"] = len(edges_data)
            logger.info(f"Exported {len(edges_data)} TAGGED_BY edges")
            return len(edges_data)

        except Exception as e:
            logger.error(f"Error exporting TAGGED_BY edges: {e}")
            return 0

    def export_subsystem_tags(self) -> int:
        """
        Export subsystem classification tags.

        Subsystem tags organize code into logical modules/components.
        Examples: executor, parser, storage, network

        Returns:
            Number of subsystem tags exported
        """
        return self._export_category("subsystem-name")

    def export_security_tags(self) -> int:
        """
        Export security risk level tags.

        Security tags classify methods by their security risk level.
        Examples: critical, high, medium, low

        Returns:
            Number of security tags exported
        """
        count = 0
        count += self._export_category("security-risk")
        count += self._export_category("taint-source")
        count += self._export_category("taint-sink")
        return count

    def export_complexity_tags(self) -> int:
        """
        Export cyclomatic complexity tags.

        Complexity tags provide numeric complexity metrics for methods.

        Returns:
            Number of complexity tags exported
        """
        return self._export_category("cyclomatic-complexity")

    def export_purpose_tags(self) -> int:
        """
        Export function purpose tags (LLM-enriched).

        Purpose tags contain semantic descriptions of what functions do.
        These are typically generated by LLM enrichment passes.

        Returns:
            Number of purpose tags exported
        """
        return self._export_category("function-purpose")

    def export_performance_tags(self) -> int:
        """
        Export performance hotspot tags.

        Performance tags mark methods that are performance critical.

        Returns:
            Number of performance tags exported
        """
        return self._export_category("perf-hotspot")


# =============================================================================
# Utility Functions
# =============================================================================

def get_tag_categories() -> Dict[str, Dict]:
    """
    Get all defined tag categories and their metadata.

    Returns:
        Dictionary of tag categories with descriptions and metadata
    """
    return TAG_CATEGORIES.copy()


def get_tag_statistics(conn) -> Dict[str, Any]:
    """
    Get statistics about tags in DuckDB.

    Args:
        conn: DuckDB connection

    Returns:
        Dictionary with tag statistics
    """
    stats = {
        "total_tags": 0,
        "total_edges": 0,
        "categories": {}
    }

    try:
        # Total tag count
        result = conn.execute("SELECT COUNT(*) FROM nodes_tag").fetchone()
        stats["total_tags"] = result[0] if result else 0

        # Total edge count
        result = conn.execute("SELECT COUNT(*) FROM edges_tagged_by").fetchone()
        stats["total_edges"] = result[0] if result else 0

        # Category breakdown
        results = conn.execute("""
            SELECT name, COUNT(*) as cnt
            FROM nodes_tag
            GROUP BY name
            ORDER BY cnt DESC
        """).fetchall()

        for row in results:
            stats["categories"][row[0]] = row[1]

    except Exception as e:
        logger.error(f"Error getting tag statistics: {e}")

    return stats


def query_tags_by_category(conn, category: str) -> List[Dict]:
    """
    Query tags by category name.

    Args:
        conn: DuckDB connection
        category: Tag category to query (supports LIKE patterns)

    Returns:
        List of tag dictionaries
    """
    try:
        results = conn.execute("""
            SELECT id, name, value
            FROM nodes_tag
            WHERE name LIKE ?
            ORDER BY value
        """, [f"{category}%"]).fetchall()

        return [{"id": r[0], "name": r[1], "value": r[2]} for r in results]

    except Exception as e:
        logger.error(f"Error querying tags: {e}")
        return []


def get_method_tags(conn, method_id: int) -> List[Dict]:
    """
    Get all tags for a specific method.

    Args:
        conn: DuckDB connection
        method_id: Method node ID

    Returns:
        List of tag dictionaries
    """
    try:
        results = conn.execute("""
            SELECT t.id, t.name, t.value
            FROM nodes_tag t
            JOIN edges_tagged_by e ON t.id = e.dst
            WHERE e.src = ?
        """, [method_id]).fetchall()

        return [{"id": r[0], "name": r[1], "value": r[2]} for r in results]

    except Exception as e:
        logger.error(f"Error getting method tags: {e}")
        return []


def get_methods_by_tag(conn, tag_name: str, tag_value: Optional[str] = None) -> List[Dict]:
    """
    Get all methods with a specific tag.

    Args:
        conn: DuckDB connection
        tag_name: Tag name to filter by
        tag_value: Optional tag value to filter by

    Returns:
        List of method dictionaries
    """
    try:
        if tag_value:
            results = conn.execute("""
                SELECT m.id, m.name, m.full_name, m.filename
                FROM nodes_method m
                JOIN edges_tagged_by e ON m.id = e.src
                JOIN nodes_tag t ON e.dst = t.id
                WHERE t.name = ? AND t.value = ?
            """, [tag_name, tag_value]).fetchall()
        else:
            results = conn.execute("""
                SELECT m.id, m.name, m.full_name, m.filename
                FROM nodes_method m
                JOIN edges_tagged_by e ON m.id = e.src
                JOIN nodes_tag t ON e.dst = t.id
                WHERE t.name = ?
            """, [tag_name]).fetchall()

        return [
            {"id": r[0], "name": r[1], "full_name": r[2], "filename": r[3]}
            for r in results
        ]

    except Exception as e:
        logger.error(f"Error getting methods by tag: {e}")
        return []


def validate_tag_integrity(conn) -> Dict[str, Any]:
    """
    Validate tag data integrity in DuckDB.

    Checks:
    - Orphaned tags (tags not connected to any method)
    - Invalid edge references
    - Duplicate tags

    Args:
        conn: DuckDB connection

    Returns:
        Validation report dictionary
    """
    report = {
        "valid": True,
        "orphaned_tags": 0,
        "invalid_edges": 0,
        "duplicate_tags": 0,
        "issues": []
    }

    try:
        # Check for orphaned tags
        result = conn.execute("""
            SELECT COUNT(*) FROM nodes_tag t
            WHERE NOT EXISTS (
                SELECT 1 FROM edges_tagged_by e WHERE e.dst = t.id
            )
        """).fetchone()
        report["orphaned_tags"] = result[0] if result else 0

        if report["orphaned_tags"] > 0:
            report["issues"].append(
                f"Found {report['orphaned_tags']} orphaned tags (not connected to any method)"
            )

        # Check for invalid edge references (dst not in nodes_tag)
        result = conn.execute("""
            SELECT COUNT(*) FROM edges_tagged_by e
            WHERE NOT EXISTS (
                SELECT 1 FROM nodes_tag t WHERE t.id = e.dst
            )
        """).fetchone()
        report["invalid_edges"] = result[0] if result else 0

        if report["invalid_edges"] > 0:
            report["valid"] = False
            report["issues"].append(
                f"Found {report['invalid_edges']} edges with invalid tag references"
            )

        # Check for duplicate (name, value) pairs
        result = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT name, value, COUNT(*) as cnt
                FROM nodes_tag
                GROUP BY name, value
                HAVING cnt > 1
            )
        """).fetchone()
        report["duplicate_tags"] = result[0] if result else 0

        if report["duplicate_tags"] > 0:
            report["issues"].append(
                f"Found {report['duplicate_tags']} duplicate (name, value) tag combinations"
            )

    except Exception as e:
        report["valid"] = False
        report["issues"].append(f"Validation error: {e}")

    return report


# =============================================================================
# CLI Interface (for standalone usage)
# =============================================================================

def main():
    """CLI entry point for tag export."""
    import argparse
    import duckdb

    parser = argparse.ArgumentParser(description="Export CPG tags to DuckDB")
    parser.add_argument("--db", default="cpg.duckdb", help="DuckDB database path")
    parser.add_argument("--stats", action="store_true", help="Show tag statistics")
    parser.add_argument("--validate", action="store_true", help="Validate tag integrity")
    parser.add_argument("--categories", nargs="+", help="Tag categories to export")

    args = parser.parse_args()

    conn = duckdb.connect(args.db)

    if args.stats:
        stats = get_tag_statistics(conn)
        print(f"\nTag Statistics for {args.db}:")
        print(f"  Total tags: {stats['total_tags']:,}")
        print(f"  Total edges: {stats['total_edges']:,}")
        print(f"\nCategories:")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count:,}")

    if args.validate:
        report = validate_tag_integrity(conn)
        print(f"\nTag Integrity Report:")
        print(f"  Valid: {report['valid']}")
        print(f"  Orphaned tags: {report['orphaned_tags']:,}")
        print(f"  Invalid edges: {report['invalid_edges']:,}")
        print(f"  Duplicate tags: {report['duplicate_tags']:,}")
        if report['issues']:
            print(f"\nIssues:")
            for issue in report['issues']:
                print(f"  - {issue}")

    conn.close()


if __name__ == "__main__":
    main()
