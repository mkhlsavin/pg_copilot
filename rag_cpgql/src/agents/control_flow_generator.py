"""Control Flow CPGQL Generator (Phase 7B)"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ControlFlowGenerator:
    """
    Generates CPGQL queries for control flow analysis and call chain tracing.

    Strategies:
    1. Entry Point Detection - Find main method handling the mechanism
    2. Keyword Method Search - Find related methods by keywords
    3. Call Graph Construction - Build call relationships
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
        Generate control flow CPGQL queries.

        Args:
            question: Natural language question
            context: Analysis context with domain, keywords, etc.

        Returns:
            Dictionary with:
            - entry_point_query: Query to find main entry point
            - keyword_methods_query: Query to find related methods
            - call_graph_query: Query to build call relationships
            - metadata: Generation metadata
        """
        # Extract keywords and file hints
        keywords = context.get('keywords', [])
        domain = context.get('domain', 'general')

        # Enrich keywords with flow-related terms
        enriched_keywords = self._enrich_keywords(keywords, question)

        # Detect file hint from question
        file_hint = self._extract_file_hint(question)

        # Generate 3 types of queries
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
                'generation_method': 'template'
            }
        }

        logger.info(f"Generated control flow queries: entry_point={bool(entry_point_query)}, "
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
        Generate query to find entry point method.

        Strategy:
        - Use file hint if available
        - Match method name patterns from keywords
        - Look for "Main", "Process", "Handle" suffixes
        """
        # Build method name pattern from keywords
        method_patterns = []

        # Add keyword-based patterns
        for keyword in keywords[:5]:  # Use top 5 keywords
            if len(keyword) >= 4:  # Skip short keywords
                # Capitalize first letter for pattern matching
                pattern = f".*{keyword[0].upper()}{keyword[1:].lower()}.*"
                method_patterns.append(pattern)

        # Add common entry point patterns
        entry_patterns = [
            ".*Main.*", ".*Process.*", ".*Handle.*", ".*Worker.*",
            ".*Manager.*", ".*Start.*", ".*Init.*"
        ]

        # Combine patterns (limit to avoid too broad search)
        if method_patterns:
            combined_pattern = "|".join(method_patterns[:3])
        else:
            combined_pattern = "|".join(entry_patterns[:2])

        # Build query
        query_parts = []
        query_parts.append("// Find entry point for the mechanism")
        query_parts.append("val entryPoint = cpg.method")

        # Add name filter
        query_parts.append(f'  .filter(_.name.matches("{combined_pattern}"))')

        # Add file filter if available
        if file_hint:
            file_pattern = file_hint.replace('.c', '.*')
            query_parts.append(f'  .filter(_.filename.matches(".*{file_pattern}"))')

        query_parts.append("  .l.headOption")
        query_parts.append("")
        query_parts.append("entryPoint.map { m =>")
        query_parts.append("  Map(")
        query_parts.append('    "method" -> m.name,')
        query_parts.append('    "file" -> m.filename,')
        query_parts.append('    "line" -> m.lineNumber.getOrElse(0),')
        query_parts.append('    "calls_to" -> m.callOut.name.l.take(10)')
        query_parts.append("  )")
        query_parts.append("}")

        return "\n".join(query_parts)

    def _generate_keyword_methods_query(
        self,
        keywords: List[str],
        file_hint: Optional[str],
        domain: str
    ) -> str:
        """
        Generate query to find methods by keywords.

        Strategy:
        - Match method names containing keywords
        - Filter by relevant files based on domain
        - Return top 10 matches with call info
        """
        # Build method name patterns from keywords
        keyword_patterns = []
        for keyword in keywords[:8]:  # Use top 8 keywords
            if len(keyword) >= 4:  # Skip short keywords
                # Case-insensitive pattern
                pattern = f".*[{keyword[0].upper()}{keyword[0].lower()}]{keyword[1:].lower()}.*"
                keyword_patterns.append(pattern)

        if not keyword_patterns:
            keyword_patterns = [".*Process.*", ".*Handle.*"]

        combined_pattern = "|".join(keyword_patterns)

        # Build file patterns based on domain
        domain_file_patterns = {
            'replication': '.*worker.*|.*replication.*|.*logical.*',
            'transaction': '.*xact.*|.*transaction.*|.*commit.*',
            'wal': '.*wal.*|.*xlog.*|.*recovery.*',
            'memory': '.*memory.*|.*palloc.*|.*buffer.*',
            'locking': '.*lock.*|.*lwlock.*',
            'vacuum': '.*vacuum.*|.*autovacuum.*',
            'checkpoint': '.*checkpoint.*|.*bgwriter.*'
        }

        file_pattern = domain_file_patterns.get(domain, '.*')

        # Build query
        query_parts = []
        query_parts.append("// Find methods related to keywords")
        query_parts.append("cpg.method")
        query_parts.append(f'  .filter(_.name.matches("{combined_pattern}"))')

        if file_hint:
            file_base = file_hint.replace('.c', '')
            query_parts.append(f'  .filter(_.filename.matches(".*{file_base}.*|{file_pattern}"))')
        else:
            query_parts.append(f'  .filter(_.filename.matches("{file_pattern}"))')

        query_parts.append("  .l.take(10)")
        query_parts.append("  .map { m =>")
        query_parts.append("    Map(")
        query_parts.append('      "method" -> m.name,')
        query_parts.append('      "file" -> m.filename,')
        query_parts.append('      "line" -> m.lineNumber.getOrElse(0),')
        query_parts.append('      "calls_to" -> m.callOut.name.l.take(5),')
        query_parts.append('      "called_by" -> List()')
        query_parts.append("    )")
        query_parts.append("  }")

        return "\n".join(query_parts)

    def _generate_call_graph_query(self, keywords: List[str]) -> str:
        """
        Generate query to build call graph for specific methods.

        Strategy:
        - Focus on key methods likely involved in mechanism
        - Get both callers and callees
        - Build bidirectional graph
        """
        # Identify key method names from keywords
        # Common PostgreSQL functions related to control flow
        key_methods = []

        # Map keywords to known PostgreSQL functions
        keyword_to_functions = {
            'abort': ['AbortCurrentTransaction', 'AbortTransaction'],
            'commit': ['CommitTransaction', 'CommitTransactionCommand'],
            'shutdown': ['ShutdownXLOG', 'proc_exit'],
            'checkpoint': ['CreateCheckPoint', 'RequestCheckpoint'],
            'replication': ['StartReplication', 'ReplicationSlotMarkXmin'],
            'interrupt': ['HandleInterrupts', 'ProcessInterrupts'],
            'cleanup': ['CleanupTransaction', 'ProcKill']
        }

        # Add functions based on keywords
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for key_term, functions in keyword_to_functions.items():
                if key_term in keyword_lower:
                    key_methods.extend(functions)

        # If no specific methods identified, use generic patterns
        if not key_methods:
            # Build pattern from keywords
            patterns = [f".*{kw[:5].capitalize()}.*" for kw in keywords[:3] if len(kw) >= 4]
            pattern_str = "|".join(patterns) if patterns else ".*Process.*|.*Handle.*"

            query_parts = []
            query_parts.append("// Build call graph from keyword-matched methods")
            query_parts.append("cpg.method")
            query_parts.append(f'  .filter(_.name.matches("{pattern_str}"))')
            query_parts.append("  .l.take(5)")
            query_parts.append("  .map { m =>")
            query_parts.append("    Map(")
            query_parts.append('      "method" -> m.name,')
            query_parts.append('      "file" -> m.filename,')
            query_parts.append('      "line" -> m.lineNumber.getOrElse(0),')
            query_parts.append('      "calls_to" -> m.callOut.name.l.take(5),')
            query_parts.append('      "called_by" -> List()')
            query_parts.append("    )")
            query_parts.append("  }")

            return "\n".join(query_parts)

        # Use specific known methods
        methods_str = ", ".join([f'"{m}"' for m in key_methods[:5]])

        query_parts = []
        query_parts.append("// Build call graph for key functions")
        query_parts.append(f"val keyMethods = List({methods_str})")
        query_parts.append("")
        query_parts.append("keyMethods.flatMap { methodName =>")
        query_parts.append("  cpg.method.name(methodName).l.headOption.map { m =>")
        query_parts.append("    Map(")
        query_parts.append('      "method" -> m.name,')
        query_parts.append('      "file" -> m.filename,')
        query_parts.append('      "line" -> m.lineNumber.getOrElse(0),')
        query_parts.append('      "calls_to" -> m.callOut.name.l.take(5),')
        query_parts.append('      "called_by" -> List()')
        query_parts.append("    )")
        query_parts.append("  }")
        query_parts.append("}")

        return "\n".join(query_parts)

    def generate_with_llm(self, question: str, context: Dict) -> Dict:
        """
        Generate queries using LLM (advanced mode).

        Falls back to template-based generation if LLM not available.
        """
        if self.llm is None:
            logger.debug("LLM not available, using template-based generation")
            return self.generate(question, context)

        # TODO: Implement LLM-based generation (Phase 7B enhancement)
        # For now, use template-based approach
        logger.info("LLM-based generation not yet implemented, using templates")
        return self.generate(question, context)
