"""Control Flow SQL Query Generator (Migrated from CPGQL to SQL)

Generates SQL queries for DuckDB CPG for control flow analysis and call chain tracing.

Strategies:
1. Entry Point Detection - Find main method handling the mechanism
2. Keyword Method Search - Find related methods by keywords
3. Call Graph Construction - Build call relationships via edges_call
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ControlFlowGenerator:
    """
    Generates SQL queries for control flow analysis and call chain tracing.

    Replaces legacy CPGQL generation with SQL queries for DuckDB CPG.
    """

    def __init__(self, llm=None):
        """
        Initialize Control Flow Generator.

        Args:
            llm: Optional LLM for advanced query generation
        """
        self.llm = llm

        # Control flow keywords mapping
        self.flow_keywords = {
            'shutdown': ['shutdown', 'cleanup', 'exit', 'terminate', 'stop'],
            'startup': ['startup', 'init', 'initialize', 'start', 'launch'],
            'consistency': ['consistent', 'consistency', 'ensure', 'guarantee', 'verify'],
            'transaction': ['transaction', 'xact', 'commit', 'abort', 'rollback'],
            'checkpoint': ['checkpoint', 'sync', 'flush', 'write', 'persist'],
            'replication': ['replication', 'replicate', 'replica', 'standby', 'primary'],
            'locking': ['lock', 'unlock', 'acquire', 'release', 'wait'],
            'error': ['error', 'exception', 'fail', 'abort', 'panic'],
            'signal': ['signal', 'interrupt', 'sigterm', 'sigusr'],
            'process': ['process', 'worker', 'background', 'bgworker']
        }

    def generate(self, question: str, context: Dict) -> Dict:
        """
        Generate control flow SQL queries.

        Args:
            question: Natural language question
            context: Analysis context with domain, keywords, etc.

        Returns:
            Dictionary with:
            - entry_point_query: SQL to find main entry point
            - keyword_methods_query: SQL to find related methods
            - call_graph_query: SQL to build call relationships
            - metadata: Generation metadata
        """
        # Extract keywords and file hints
        keywords = context.get('keywords', [])
        domain = context.get('domain', 'general')

        # Enrich keywords with flow-related terms
        enriched_keywords = self._enrich_keywords(keywords, question)

        # Detect file hint from question
        file_hint = self._extract_file_hint(question)

        # Generate 3 types of SQL queries
        entry_point_query = self._generate_entry_point_query(
            question, enriched_keywords, file_hint
        )

        keyword_methods_query = self._generate_keyword_methods_query(
            enriched_keywords, file_hint, domain
        )

        call_graph_query = self._generate_call_graph_query(
            enriched_keywords
        )

        result = {
            'entry_point_query': entry_point_query,
            'keyword_methods_query': keyword_methods_query,
            'call_graph_query': call_graph_query,
            'metadata': {
                'enriched_keywords': enriched_keywords,
                'file_hint': file_hint,
                'domain': domain,
                'generation_method': 'sql_template'
            }
        }

        logger.info(f"Generated control flow SQL queries: entry_point={bool(entry_point_query)}, "
                   f"keyword_methods={bool(keyword_methods_query)}, call_graph={bool(call_graph_query)}")

        return result

    def _enrich_keywords(self, keywords: List[str], question: str) -> List[str]:
        """
        Enrich keywords with flow-related terms.

        Args:
            keywords: Original keywords from question analysis
            question: Full question text

        Returns:
            Enriched keyword list
        """
        enriched = set(keywords)
        question_lower = question.lower()

        # Add flow keywords if mentioned
        for category, terms in self.flow_keywords.items():
            for term in terms:
                if term in question_lower:
                    enriched.add(term)

        # Extract camelCase/snake_case identifiers
        camel_case = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', question)
        snake_case = re.findall(r'\b[a-z]+_[a-z_]+\b', question)

        enriched.update(camel_case)
        enriched.update(snake_case)

        return list(enriched)

    def _extract_file_hint(self, question: str) -> Optional[str]:
        """
        Extract file hint from question (e.g., worker.c:4097).

        Args:
            question: Question text

        Returns:
            File name or None
        """
        # Match patterns like: worker.c, worker.c:4097, backend/worker.c
        file_match = re.search(r'\b([a-z_]+\.c)(?::\d+)?\b', question.lower())
        if file_match:
            return file_match.group(1)

        # Match directory patterns: backend/commands/trigger.c
        path_match = re.search(r'\b([\w/]+/[\w]+\.c)\b', question)
        if path_match:
            filename = path_match.group(1).split('/')[-1]
            return filename

        return None

    def _generate_entry_point_query(
        self,
        question: str,
        keywords: List[str],
        file_hint: Optional[str]
    ) -> str:
        """
        Generate SQL query to find entry point method.

        Strategy:
        - Use file hint if available
        - Match method name patterns from keywords
        - Look for "Main", "Process", "Handle" suffixes
        """
        # Build LIKE conditions from keywords
        like_conditions = []

        # Add keyword-based patterns
        for keyword in keywords[:5]:  # Use top 5 keywords
            if len(keyword) >= 4:  # Skip short keywords
                like_conditions.append(f"m.name ILIKE '%{keyword}%'")

        # Add common entry point patterns
        entry_patterns = ['Main', 'Process', 'Handle', 'Worker', 'Manager', 'Start', 'Init']
        for pattern in entry_patterns[:3]:
            like_conditions.append(f"m.name ILIKE '%{pattern}%'")

        # Combine conditions with OR
        where_clause = " OR ".join(like_conditions) if like_conditions else "1=1"

        # Add file filter if available
        if file_hint:
            file_pattern = file_hint.replace('.c', '')
            where_clause = f"({where_clause}) AND m.filename ILIKE '%{file_pattern}%'"

        # Build SQL query
        query = f"""
-- Find entry point for the mechanism
SELECT
    m.id,
    m.name AS method,
    m.filename AS file,
    m.line_number AS line,
    (SELECT STRING_AGG(callee.name, ', ')
     FROM edges_call ec
     JOIN nodes_call c ON ec.src = c.id
     JOIN nodes_method callee ON ec.dst = callee.id
     WHERE c.containing_method_id = m.id
     LIMIT 10) AS calls_to
FROM nodes_method m
WHERE {where_clause}
LIMIT 1
"""
        return query.strip()

    def _generate_keyword_methods_query(
        self,
        keywords: List[str],
        file_hint: Optional[str],
        domain: str
    ) -> str:
        """
        Generate SQL query to find methods by keywords.

        Strategy:
        - Match method names containing keywords
        - Filter by relevant files based on domain
        - Return top 10 matches with call info
        """
        # Build LIKE conditions from keywords
        like_conditions = []
        for keyword in keywords[:8]:  # Use top 8 keywords
            if len(keyword) >= 4:  # Skip short keywords
                like_conditions.append(f"m.name ILIKE '%{keyword}%'")

        if not like_conditions:
            like_conditions = ["m.name ILIKE '%Process%'", "m.name ILIKE '%Handle%'"]

        where_clause = " OR ".join(like_conditions)

        # Add file patterns based on domain
        domain_file_patterns = {
            'replication': ['worker', 'replication', 'logical'],
            'transaction': ['xact', 'transaction', 'commit'],
            'wal': ['wal', 'xlog', 'recovery'],
            'memory': ['memory', 'palloc', 'buffer'],
            'locking': ['lock', 'lwlock'],
            'vacuum': ['vacuum', 'autovacuum'],
            'checkpoint': ['checkpoint', 'bgwriter']
        }

        file_conditions = []
        if domain in domain_file_patterns:
            for pattern in domain_file_patterns[domain]:
                file_conditions.append(f"m.filename ILIKE '%{pattern}%'")

        if file_hint:
            file_base = file_hint.replace('.c', '')
            file_conditions.append(f"m.filename ILIKE '%{file_base}%'")

        if file_conditions:
            file_clause = " OR ".join(file_conditions)
            where_clause = f"({where_clause}) AND ({file_clause})"

        # Build SQL query
        query = f"""
-- Find methods related to keywords
SELECT
    m.name AS method,
    m.filename AS file,
    m.line_number AS line,
    (SELECT STRING_AGG(DISTINCT callee.name, ', ')
     FROM edges_call ec
     JOIN nodes_call c ON ec.src = c.id
     JOIN nodes_method callee ON ec.dst = callee.id
     WHERE c.containing_method_id = m.id
     LIMIT 5) AS calls_to
FROM nodes_method m
WHERE {where_clause}
LIMIT 10
"""
        return query.strip()

    def _generate_call_graph_query(self, keywords: List[str]) -> str:
        """
        Generate SQL query to build call graph for specific methods.

        Strategy:
        - Focus on key methods likely involved in mechanism
        - Use recursive CTE for call chain traversal
        - Get both callers and callees
        """
        # Build LIKE conditions from keywords
        like_conditions = []
        for keyword in keywords[:5]:
            if len(keyword) >= 4:
                like_conditions.append(f"m.name ILIKE '%{keyword}%'")

        if not like_conditions:
            like_conditions = ["m.name ILIKE '%Process%'", "m.name ILIKE '%Handle%'"]

        where_clause = " OR ".join(like_conditions)

        # Build recursive CTE query for call graph
        query = f"""
-- Build call graph from keyword-matched methods
WITH RECURSIVE call_chain AS (
    -- Base case: find starting methods
    SELECT
        m.id AS method_id,
        m.name AS method_name,
        m.filename,
        m.line_number,
        1 AS depth
    FROM nodes_method m
    WHERE {where_clause}
    LIMIT 5

    UNION ALL

    -- Recursive case: find callees
    SELECT
        callee.id,
        callee.name,
        callee.filename,
        callee.line_number,
        cc.depth + 1
    FROM call_chain cc
    JOIN nodes_call c ON c.containing_method_id = cc.method_id
    JOIN edges_call ec ON ec.src = c.id
    JOIN nodes_method callee ON ec.dst = callee.id
    WHERE cc.depth < 3
)
SELECT DISTINCT
    method_name AS method,
    filename AS file,
    line_number AS line,
    depth
FROM call_chain
ORDER BY depth, method_name
LIMIT 20
"""
        return query.strip()

    def generate_with_llm(self, question: str, context: Dict) -> Dict:
        """
        Generate queries using LLM (advanced mode).

        Uses the LLM to generate more sophisticated SQL queries
        based on the question and context. Falls back to template-based
        generation if LLM not available or on error.

        Args:
            question: Natural language question
            context: Analysis context with domain, keywords, sql_examples, etc.

        Returns:
            Dictionary with generated queries and metadata
        """
        if self.llm is None:
            logger.debug("LLM not available, using template-based generation")
            return self.generate(question, context)

        try:
            # Build prompt for LLM
            prompt = self._build_llm_prompt(question, context)

            # Generate with LLM
            logger.info("Generating control flow SQL queries with LLM")
            response = self.llm.generate(
                prompt,
                temperature=0.1,  # Low temperature for deterministic queries
                max_tokens=1024,
            )

            # Parse LLM response
            parsed = self._parse_llm_response(response, question, context)

            if parsed and self._validate_llm_queries(parsed):
                parsed['metadata'] = {
                    **parsed.get('metadata', {}),
                    'generation_method': 'llm',
                    'llm_confidence': parsed.get('confidence', 0.8),
                }
                logger.info("LLM-based generation successful")
                return parsed

            logger.warning("LLM output validation failed, falling back to templates")

        except Exception as e:
            logger.warning(f"LLM generation failed: {e}, falling back to templates")

        # Fallback to template-based generation
        return self.generate(question, context)

    def _build_llm_prompt(self, question: str, context: Dict) -> str:
        """Build prompt for LLM-based SQL query generation."""
        keywords = context.get('keywords', [])
        domain = context.get('domain', 'general')
        sql_examples = context.get('sql_examples', [])

        # Format examples
        examples_text = ""
        if sql_examples:
            examples_text = "\nExamples of valid SQL queries:\n"
            for i, ex in enumerate(sql_examples[:5], 1):
                if isinstance(ex, dict):
                    examples_text += f"{i}. {ex.get('query', ex)}\n"
                else:
                    examples_text += f"{i}. {ex}\n"

        prompt = f"""Generate SQL queries for control flow analysis on DuckDB CPG.

Question: {question}

Domain: {domain}
Keywords: {', '.join(keywords) if keywords else 'none'}
{examples_text}

Database Schema:
- nodes_method: id, name, full_name, filename, line_number, signature
- nodes_call: id, name, code, filename, line_number, containing_method_id
- edges_call: src (nodes_call.id), dst (nodes_method.id)

Generate 3 types of SQL queries:
1. entry_point_query - Find the main entry point method
2. keyword_methods_query - Find methods related to the keywords
3. call_graph_query - Build call relationships using recursive CTE

Output format (JSON):
{{
  "entry_point_query": "SELECT ...",
  "keyword_methods_query": "SELECT ...",
  "call_graph_query": "WITH RECURSIVE ...",
  "confidence": 0.0-1.0
}}

Generate valid SQL queries only. No explanations."""

        return prompt

    def _parse_llm_response(self, response: str, question: str, context: Dict) -> Optional[Dict]:
        """Parse LLM response to extract queries."""
        import json

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*"entry_point_query"[^{}]*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result

            # Try parsing entire response as JSON
            result = json.loads(response.strip())
            return result

        except json.JSONDecodeError:
            # Try to extract queries manually
            result = {}

            # Extract entry_point_query
            match = re.search(r'"?entry_point_query"?\s*[:=]\s*["\']?(SELECT[^"\']+)["\']?', response, re.IGNORECASE)
            if match:
                result['entry_point_query'] = match.group(1).strip()

            # Extract keyword_methods_query
            match = re.search(r'"?keyword_methods_query"?\s*[:=]\s*["\']?(SELECT[^"\']+)["\']?', response, re.IGNORECASE)
            if match:
                result['keyword_methods_query'] = match.group(1).strip()

            # Extract call_graph_query
            match = re.search(r'"?call_graph_query"?\s*[:=]\s*["\']?((?:WITH|SELECT)[^"\']+)["\']?', response, re.IGNORECASE)
            if match:
                result['call_graph_query'] = match.group(1).strip()

            if result:
                result['confidence'] = 0.6  # Lower confidence for manual extraction
                return result

        except Exception as e:
            logger.debug(f"Failed to parse LLM response: {e}")

        return None

    def _validate_llm_queries(self, parsed: Dict) -> bool:
        """Validate that parsed queries are syntactically correct SQL."""
        required_keys = ['entry_point_query', 'keyword_methods_query', 'call_graph_query']

        # Check at least one query exists
        has_query = any(parsed.get(key) for key in required_keys)
        if not has_query:
            return False

        # Basic SQL syntax validation
        for key in required_keys:
            query = parsed.get(key, '')
            if query:
                query_upper = query.upper().strip()
                # Must start with SELECT or WITH
                if not (query_upper.startswith('SELECT') or query_upper.startswith('WITH')):
                    logger.debug(f"Query '{key}' does not start with SELECT or WITH")
                    return False

                # Basic bracket balance check
                if query.count('(') != query.count(')'):
                    logger.debug(f"Query '{key}' has unbalanced parentheses")
                    return False

        return True
