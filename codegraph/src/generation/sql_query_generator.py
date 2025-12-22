"""SQL/PGQ Query Generator for DuckDB CPG - Natural Language to SQL Translation

This module generates SQL and SQL/PGQ queries for DuckDB CPG from natural language
questions, providing an alternative to CPGQL for querying Code Property Graphs.

Supports:
- Call graph queries (direct calls, call chains, callers/callees)
- Data flow queries (REACHING_DEF paths, variable tracking)
- AST/CFG traversal queries
- Pattern matching (method names, file patterns)
- Statistical queries (top callers, most called methods)
"""

import logging
import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLQueryGenerator:
    """Generate SQL/PGQ queries for DuckDB CPG from natural language questions"""

    # Query pattern templates
    QUERY_TEMPLATES = {
        # Call graph patterns
        "find_method": """
            SELECT id, name, full_name, filename, line_number, signature
            FROM nodes_method
            WHERE {condition}
            LIMIT {limit};
        """,

        "find_callees": """
            SELECT DISTINCT
                callee.name AS method_name,
                callee.full_name,
                callee.filename,
                callee.line_number
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            JOIN nodes_method callee ON ec.dst = callee.id
            WHERE caller.name = '{method_name}'
            LIMIT {limit};
        """,

        "find_callers": """
            SELECT DISTINCT
                caller.name AS caller_name,
                caller.full_name,
                caller.filename,
                caller.line_number
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method callee ON ec.dst = callee.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            WHERE callee.name = '{method_name}'
            LIMIT {limit};
        """,

        "call_chain": """
            WITH RECURSIVE call_chain AS (
                -- Base case
                SELECT ec.src, ec.dst, 1 as depth
                FROM edges_call ec
                JOIN nodes_call c ON ec.src = c.id
                JOIN nodes_method m_start ON c.containing_method_id = m_start.id
                WHERE m_start.name = '{method_name}'

                UNION ALL

                -- Recursive case
                SELECT ec2.src, ec2.dst, cc.depth + 1
                FROM edges_call ec2
                JOIN call_chain cc ON ec2.src IN (
                    SELECT c2.id FROM nodes_call c2
                    WHERE c2.containing_method_id = cc.dst
                )
                WHERE cc.depth < {max_depth}
            )
            SELECT DISTINCT
                m.name,
                m.full_name,
                m.filename,
                m.line_number,
                MIN(cc.depth) as depth
            FROM call_chain cc
            JOIN nodes_method m ON cc.dst = m.id
            GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number
            ORDER BY depth, m.name
            LIMIT {limit};
        """,

        # Statistical queries
        "top_callers": """
            SELECT
                m.name,
                m.full_name,
                m.filename,
                COUNT(DISTINCT c.id) as call_count
            FROM nodes_method m
            LEFT JOIN nodes_call c ON c.containing_method_id = m.id
            GROUP BY m.id, m.name, m.full_name, m.filename
            ORDER BY call_count DESC
            LIMIT {limit};
        """,

        "top_callees": """
            SELECT
                m.name,
                m.full_name,
                m.filename,
                COUNT(ec.src) as called_count
            FROM nodes_method m
            LEFT JOIN edges_call ec ON m.id = ec.dst
            GROUP BY m.id, m.name, m.full_name, m.filename
            ORDER BY called_count DESC
            LIMIT {limit};
        """,

        # Data flow patterns
        "data_flow": """
            WITH RECURSIVE data_flow AS (
                -- Base case
                SELECT src, dst, variable, 1 as hops
                FROM edges_reaching_def
                WHERE variable = '{variable_name}'

                UNION ALL

                -- Recursive case
                SELECT erd.src, erd.dst, erd.variable, df.hops + 1
                FROM edges_reaching_def erd
                JOIN data_flow df ON erd.src = df.dst
                WHERE df.hops < {max_hops}
                  AND erd.variable = '{variable_name}'
            )
            SELECT DISTINCT src, dst, variable, hops
            FROM data_flow
            ORDER BY hops
            LIMIT {limit};
        """,

        # Pattern matching
        "pattern_match": """
            SELECT
                caller.name AS caller_name,
                caller.full_name AS caller_full_name,
                callee.name AS callee_name,
                callee.full_name AS callee_full_name,
                caller.filename
            FROM edges_call ec
            JOIN nodes_call c ON ec.src = c.id
            JOIN nodes_method caller ON c.containing_method_id = caller.id
            JOIN nodes_method callee ON ec.dst = callee.id
            WHERE {condition}
            LIMIT {limit};
        """,

        # File-based queries
        "methods_in_file": """
            SELECT name, full_name, line_number, signature, filename
            FROM nodes_method
            WHERE LOWER(filename) LIKE LOWER('%{filename}%')
            ORDER BY line_number
            LIMIT {limit};
        """
    }

    # Few-shot examples for prompt
    EXAMPLES = [
        {
            "question": "Find all methods called by main",
            "query": "find_callees",
            "params": {"method_name": "main", "limit": 100},
            "sql": """SELECT DISTINCT
    callee.name AS method_name,
    callee.full_name,
    callee.filename,
    callee.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.containing_method_id = caller.id
JOIN nodes_method callee ON ec.dst = callee.id
WHERE caller.name = 'main'
LIMIT 100;"""
        },
        {
            "question": "What methods call malloc?",
            "query": "find_callers",
            "params": {"method_name": "malloc", "limit": 100},
            "sql": """SELECT DISTINCT
    caller.name AS caller_name,
    caller.full_name,
    caller.filename,
    caller.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method callee ON ec.dst = callee.id
JOIN nodes_method caller ON c.containing_method_id = caller.id
WHERE callee.name = 'malloc'
LIMIT 100;"""
        },
        {
            "question": "Show me the call chain from main with depth 3",
            "query": "call_chain",
            "params": {"method_name": "main", "max_depth": 3, "limit": 100},
            "sql": """WITH RECURSIVE call_chain AS (
    SELECT ec.src, ec.dst, 1 as depth
    FROM edges_call ec
    JOIN nodes_call c ON ec.src = c.id
    JOIN nodes_method m_start ON c.containing_method_id = m_start.id
    WHERE m_start.name = 'main'

    UNION ALL

    SELECT ec2.src, ec2.dst, cc.depth + 1
    FROM edges_call ec2
    JOIN call_chain cc ON ec2.src IN (
        SELECT c2.id FROM nodes_call c2
        WHERE c2.method_full_name IN (
            SELECT m2.full_name FROM nodes_method m2 WHERE m2.id = cc.dst
        )
    )
    WHERE cc.depth < 3
)
SELECT DISTINCT
    m.name,
    m.full_name,
    m.filename,
    m.line_number,
    MIN(cc.depth) as depth
FROM call_chain cc
JOIN nodes_method m ON cc.dst = m.id
GROUP BY m.id, m.name, m.full_name, m.filename, m.line_number
ORDER BY depth, m.name
LIMIT 100;"""
        },
        {
            "question": "Which methods make the most calls?",
            "query": "top_callers",
            "params": {"limit": 10},
            "sql": """SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT c.id) as call_count
FROM nodes_method m
LEFT JOIN nodes_call c ON c.containing_method_id = m.id
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY call_count DESC
LIMIT 10;"""
        },
        {
            "question": "Find methods containing 'process' in file.c",
            "query": "pattern_match",
            "params": {"method_pattern": "%process%", "filename": "file.c", "limit": 50},
            "sql": """SELECT name, full_name, line_number, signature
FROM nodes_method
WHERE name LIKE '%process%'
  AND filename LIKE '%file.c%'
LIMIT 50;"""
        }
    ]

    def __init__(self, llm=None):
        """
        Initialize SQL query generator

        Args:
            llm: Optional LLM interface for advanced query generation
        """
        self.llm = llm

    def generate_query(
        self,
        question: str,
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> Dict[str, any]:
        """
        Generate SQL query from natural language question

        Args:
            question: Natural language question about code
            max_tokens: Maximum tokens for LLM generation
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Dict with 'query' (SQL string), 'template' (template name), 'params' (parameters)
        """
        # Try pattern matching first (rule-based)
        result = self._pattern_match_query(question)

        if result:
            logger.info(f"Pattern-matched query: {result['template']}")
            return result

        # Fallback to LLM generation if available
        if self.llm:
            logger.info("Using LLM for query generation")
            return self._llm_generate_query(question, max_tokens, temperature)

        # Final fallback: simple method search
        logger.warning("No pattern match or LLM available, using fallback query")
        return self._fallback_query(question)

    def _pattern_match_query(self, question: str) -> Optional[Dict[str, any]]:
        """
        Use rule-based pattern matching to generate query

        Args:
            question: Natural language question

        Returns:
            Query dict if pattern matched, None otherwise
        """
        question_lower = question.lower()

        # Extract method names (look for quoted strings or capitalized names)
        method_names = re.findall(r"'([^']+)'|\"([^\"]+)\"|`([^`]+)`", question)
        method_name = next((m for m in sum(method_names, ()) if m), None)

        # Extract numbers (for limits, depths)
        numbers = re.findall(r'\b(\d+)\b', question)
        limit = int(numbers[0]) if numbers else 100

        # Pattern 2: Find callers (who calls X?) - Check this FIRST (more specific)
        if any(pattern in question_lower for pattern in ["who calls", "callers of", "what calls"]):
            if method_name:
                return {
                    "query": self.QUERY_TEMPLATES["find_callers"].format(
                        method_name=method_name,
                        limit=limit
                    ),
                    "template": "find_callers",
                    "params": {"method_name": method_name, "limit": limit}
                }

        # Pattern 1: Find callees (what does X call?)
        if any(pattern in question_lower for pattern in ["what does", "calls", "invokes", "callees of"]):
            if method_name:
                return {
                    "query": self.QUERY_TEMPLATES["find_callees"].format(
                        method_name=method_name,
                        limit=limit
                    ),
                    "template": "find_callees",
                    "params": {"method_name": method_name, "limit": limit}
                }

        # Pattern 3: Call chain
        if any(pattern in question_lower for pattern in ["call chain", "call path", "execution path"]):
            max_depth = int(numbers[0]) if numbers else 5
            if method_name:
                return {
                    "query": self.QUERY_TEMPLATES["call_chain"].format(
                        method_name=method_name,
                        max_depth=max_depth,
                        limit=limit
                    ),
                    "template": "call_chain",
                    "params": {"method_name": method_name, "max_depth": max_depth, "limit": limit}
                }

        # Pattern 4: Top callers
        if any(pattern in question_lower for pattern in ["most calls", "top callers", "methods with most"]):
            return {
                "query": self.QUERY_TEMPLATES["top_callers"].format(limit=limit),
                "template": "top_callers",
                "params": {"limit": limit}
            }

        # Pattern 5: Most called (top callees)
        if any(pattern in question_lower for pattern in ["most called", "frequently called", "top callees"]):
            return {
                "query": self.QUERY_TEMPLATES["top_callees"].format(limit=limit),
                "template": "top_callees",
                "params": {"limit": limit}
            }

        # Pattern 6: Data flow
        if any(pattern in question_lower for pattern in ["data flow", "variable flow", "reaches"]):
            var_name = method_name or "userInput"  # Default variable
            max_hops = int(numbers[0]) if numbers else 5
            return {
                "query": self.QUERY_TEMPLATES["data_flow"].format(
                    variable_name=var_name,
                    max_hops=max_hops,
                    limit=limit
                ),
                "template": "data_flow",
                "params": {"variable_name": var_name, "max_hops": max_hops, "limit": limit}
            }

        # Pattern 7: Methods in file
        if any(pattern in question_lower for pattern in ["in file", "from file", "in ", "methods in"]):
            # Extract filename - look for file extensions
            filename_match = re.search(r'(?:in|from)\s+(?:file\s+)?([^\s]+\.[a-z]+)', question_lower)
            if not filename_match:
                # Try to find any word with file extension
                filename_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*\.[a-z]+)', question)
            if filename_match:
                filename = filename_match.group(1)
                return {
                    "query": self.QUERY_TEMPLATES["methods_in_file"].format(
                        filename=filename,
                        limit=limit
                    ),
                    "template": "methods_in_file",
                    "params": {"filename": filename, "limit": limit}
                }

        # Pattern 8: Find method by name
        if any(pattern in question_lower for pattern in ["find method", "get method", "show method"]):
            if method_name:
                return {
                    "query": self.QUERY_TEMPLATES["find_method"].format(
                        condition=f"LOWER(name) LIKE LOWER('%{method_name}%')",
                        limit=limit
                    ),
                    "template": "find_method",
                    "params": {"method_name": method_name, "limit": limit}
                }

        return None

    def _llm_generate_query(
        self,
        question: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, any]:
        """
        Use LLM to generate SQL query

        Args:
            question: Natural language question
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Query dict with generated SQL
        """
        prompt = self._build_llm_prompt(question)

        try:
            generated_sql = self.llm.generate_simple(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Clean up generated SQL
            cleaned_sql = self._cleanup_sql(generated_sql)

            return {
                "query": cleaned_sql,
                "template": "llm_generated",
                "params": {"question": question}
            }

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._fallback_query(question)

    def _build_llm_prompt(self, question: str) -> str:
        """
        Build few-shot prompt for LLM with strict formatting requirements

        Args:
            question: Natural language question

        Returns:
            Formatted prompt with examples and strict instructions
        """
        prompt = """You are a SQL query generator. You MUST output ONLY valid SQL - no explanations, no comments, no natural language.

CRITICAL RULES:
1. Output ONLY the SQL query - nothing else
2. Use ONLY English SQL keywords (SELECT, FROM, WHERE, JOIN, etc.)
3. Do NOT output Chinese or any non-English characters
4. Do NOT add explanations before or after the SQL
5. Do NOT add comments (no -- or /* */ comments)
6. Start directly with SELECT or WITH keyword
7. End with a semicolon
8. Use LOWER() for case-insensitive text matching

DATABASE SCHEMA:
- nodes_method (id BIGINT, name VARCHAR, full_name VARCHAR, filename VARCHAR, line_number INT, signature VARCHAR, code TEXT, is_external BOOL)
- nodes_call (id BIGINT, name VARCHAR, method_full_name VARCHAR, filename VARCHAR, line_number INT, dispatch_type VARCHAR)
- edges_call (src BIGINT, dst BIGINT) -- src is call site ID, dst is target method ID

EXAMPLES:

Question: What methods does main call?
SELECT DISTINCT
    callee.name AS method_name,
    callee.full_name,
    callee.filename,
    callee.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method caller ON c.containing_method_id = caller.id
JOIN nodes_method callee ON ec.dst = callee.id
WHERE LOWER(caller.name) = LOWER('main')
LIMIT 100;

Question: Who calls malloc?
SELECT DISTINCT
    caller.name AS caller_name,
    caller.full_name,
    caller.filename,
    caller.line_number
FROM edges_call ec
JOIN nodes_call c ON ec.src = c.id
JOIN nodes_method callee ON ec.dst = callee.id
JOIN nodes_method caller ON c.containing_method_id = caller.id
WHERE LOWER(callee.name) = LOWER('malloc')
LIMIT 100;

Question: Which methods make the most calls?
SELECT
    m.name,
    m.full_name,
    m.filename,
    COUNT(DISTINCT c.id) as call_count
FROM nodes_method m
LEFT JOIN nodes_call c ON c.containing_method_id = m.id
GROUP BY m.id, m.name, m.full_name, m.filename
ORDER BY call_count DESC
LIMIT 10;

Now translate this question into SQL. Output ONLY the SQL query, nothing else:

Question: {question}
SQL:
"""
        return prompt.format(question=question)

    def _cleanup_sql(self, sql: str) -> str:
        """
        Clean up generated SQL query

        Handles:
        - Markdown code blocks
        - Natural language comments/explanations
        - Non-English SQL keywords
        - Multi-line formatting

        Args:
            sql: Raw SQL string

        Returns:
            Cleaned SQL string
        """
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*$', '', sql)
        sql = re.sub(r'```', '', sql)

        # Split into lines for processing
        lines = sql.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip comment lines (SQL comments start with --)
            if line.startswith('--'):
                continue

            # Skip pure natural language lines (no SQL keywords)
            # Check if line contains SQL keywords
            sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP', 'ORDER',
                           'LIMIT', 'WITH', 'AS', 'ON', 'AND', 'OR', 'DISTINCT',
                           'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'UNION', 'RECURSIVE']

            line_upper = line.upper()
            has_sql_keyword = any(keyword in line_upper for keyword in sql_keywords)

            # Skip lines with only natural language (no SQL keywords and no operators/punctuation)
            if not has_sql_keyword and not any(c in line for c in ['(', ')', ',', '=', '*', ';']):
                continue

            # Check for non-English SQL keywords and skip the line
            # Common Chinese SQL keywords: 选出 (SELECT), 从 (FROM), 其中 (WHERE)
            if any(ord(c) > 127 for c in line):
                # Contains non-ASCII characters, likely non-English
                # Only keep if it has English SQL keywords
                if not has_sql_keyword:
                    continue
                # Try to fix by replacing common patterns
                line = line.replace('选出', 'SELECT')
                line = line.replace('从', 'FROM')
                line = line.replace('其中', 'WHERE')

            cleaned_lines.append(line)

        # Rejoin lines
        sql = '\n'.join(cleaned_lines)

        # Extract SQL statement if mixed with other text
        # Look for the main SQL statement starting with WITH or SELECT
        sql_match = re.search(r'((?:WITH|SELECT)\s+.+)', sql, re.IGNORECASE | re.DOTALL)
        if sql_match:
            sql = sql_match.group(1)

        # Remove trailing/leading whitespace
        sql = sql.strip()

        # Remove any remaining non-ASCII characters that aren't part of strings
        # Keep quoted strings intact
        def clean_non_ascii(text):
            result = []
            in_string = False
            quote_char = None

            for char in text:
                if char in ["'", '"'] and (not in_string or char == quote_char):
                    in_string = not in_string
                    quote_char = char if in_string else None
                    result.append(char)
                elif in_string:
                    result.append(char)
                elif ord(char) < 128 or char in ['\n', '\t', ' ']:
                    result.append(char)
                # Skip non-ASCII characters outside strings

            return ''.join(result)

        sql = clean_non_ascii(sql)

        # Ensure ends with semicolon
        if not sql.endswith(';'):
            sql += ';'

        # Validate that we have a SQL statement
        sql_upper = sql.upper()
        if not any(keyword in sql_upper for keyword in ['SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE']):
            raise ValueError(f"Cleaned output does not appear to be valid SQL: {sql[:100]}")

        return sql

    def _fallback_query(self, question: str) -> Dict[str, any]:
        """
        Generate fallback query when pattern matching and LLM fail

        Args:
            question: Natural language question

        Returns:
            Simple search query
        """
        # Extract any quoted term as search keyword
        keywords = re.findall(r"'([^']+)'|\"([^\"]+)\"|`([^`]+)`", question)
        keyword = next((k for k in sum(keywords, ()) if k), "")

        if not keyword:
            # Extract any capitalized word as potential method name
            capitalized = re.findall(r'\b([A-Z][a-z]+)\b', question)
            keyword = capitalized[0] if capitalized else ""

        condition = f"name LIKE '%{keyword}%'" if keyword else "TRUE"

        return {
            "query": self.QUERY_TEMPLATES["find_method"].format(
                condition=condition,
                limit=100
            ),
            "template": "find_method",
            "params": {"keyword": keyword, "limit": 100}
        }

    def get_template(self, template_name: str) -> Optional[str]:
        """
        Get SQL template by name

        Args:
            template_name: Template identifier

        Returns:
            Template string or None
        """
        return self.QUERY_TEMPLATES.get(template_name)

    def list_templates(self) -> List[str]:
        """
        List all available query templates

        Returns:
            List of template names
        """
        return list(self.QUERY_TEMPLATES.keys())

    def get_examples(self) -> List[Dict]:
        """
        Get few-shot examples

        Returns:
            List of example dicts
        """
        return self.EXAMPLES


def main():
    """Example usage and testing"""
    generator = SQLQueryGenerator()

    # Test pattern matching
    test_questions = [
        "What does main call?",
        "Who calls malloc?",
        "Show me the call chain from processData with depth 3",
        "Which methods make the most calls?",
        "Find methods in server.c",
        "What is the most frequently called method?",
        "Show data flow for userInput variable"
    ]

    print("=" * 80)
    print("SQL Query Generator - Test Mode")
    print("=" * 80)

    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Question: {question}")
        print("-" * 80)

        result = generator.generate_query(question)

        print(f"Template: {result['template']}")
        print(f"Params: {result['params']}")
        print(f"\nGenerated SQL:")
        print(result['query'])
        print()


if __name__ == "__main__":
    main()
