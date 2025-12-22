# ============================================================================
# DOMAIN-AGNOSTIC MODULE
# ============================================================================
# This module MUST NOT contain hardcoded domain-specific code.
# All domain-specific logic should be retrieved from:
#   - src/domains/{domain}/plugin.py via DomainRegistry
#   - src/workflow/_plugin_helpers.py helper functions
#   - src/prompts/prompt_registry.py for prompts
#
# DO NOT add:
#   - Hardcoded function names (pg_*, elog, palloc, etc.)
#   - Hardcoded SQL patterns with domain-specific terms
#   - Inline LLM prompts (use PromptRegistry)
#
# See: docs/AGENT_MIGRATION_GUIDE.md for migration patterns
# ============================================================================
"""Analyzer Agent - Extracts intent, domain, and keywords from questions."""
import logging
import json
import re
from typing import Dict, List, Tuple, Optional

# Week 5: Import CPGConfig for domain-adaptive prompts
from src.config import get_global_cpg_config, CPGConfig

# Domain plugin helpers for domain-agnostic keywords
from src.workflow._plugin_helpers import get_domain_keywords_from_plugin

logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """
    Analyzer Agent for question understanding.

    Extracts:
    - Intent: find-function | explain-concept | security-check | code-analysis
    - Domain: vacuum | wal | mvcc | query-planning | memory | replication | etc.
    - Keywords: Key terms for retrieval
    """

    def __init__(self, llm=None, cpg_config: Optional[CPGConfig] = None):
        """
        Initialize Analyzer Agent.

        Args:
            llm: Optional LLM interface for advanced analysis
            cpg_config: Optional CPGConfig for domain-specific prompts (Week 5)
        """
        self.llm = llm

        # Week 5: Get CPG config for domain-adaptive prompts
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

        # Get domain-specific analyst title
        self.code_analyst_title = cpg_config.get_code_analyst_title()

        # Domain keywords mapping - obtained from active domain plugin
        # This replaces the hardcoded PostgreSQL-specific keywords
        self.domain_keywords = get_domain_keywords_from_plugin()

        # Intent patterns
        self.intent_patterns = {
            'find-function': [
                r'\bfind\b', r'\bsearch\b', r'\blocate\b', r'\bidentify\b',
                r'\bwhich function\b', r'\bwhat function\b', r'\blist.*function\b'
            ],
            'explain-concept': [
                r'\bhow does\b', r'\bwhat is\b', r'\bexplain\b', r'\bdescribe\b',
                r'\bwhy does\b', r'\bwhat role\b', r'\bwhat.*purpose\b'
            ],
            'security-check': [
                r'\bsecurity\b', r'\bvulnerability\b', r'\bunsafe\b', r'\brisk\b',
                r'\battack\b', r'\bexploit\b', r'\bbuffer overflow\b'
            ],
            'code-analysis': [
                r'\banalyze\b', r'\bcheck\b', r'\breview\b', r'\binspect\b',
                r'\bdata flow\b', r'\btaint\b', r'\breachable\b'
            ]
        }

        # Phase 7: Query mode classification keywords
        # Used to route between semantic mode (find-method) and control flow mode (explain-logic)
        self.explain_logic_keywords = [
            'mechanism', 'ensures', 'ensure', 'handles', 'handle', 'manages', 'manage',
            'process', 'processes', 'workflow', 'how does', 'what happens',
            'during', 'when', 'coordinates', 'achieves', 'prevents',
            'guarantees', 'maintains', 'implements', 'orchestrates',
            'flow', 'sequence', 'chain', 'steps', 'procedure',
            'interaction', 'coordination', 'synchronization'
        ]

        self.find_method_keywords = [
            'purpose of', 'what is', 'what does', 'function',
            'method', 'role of', 'definition', 'implementation of',
            'located in', 'found in', 'defined in', 'where is'
        ]

    def analyze(self, question: str) -> Dict:
        """
        Analyze question to extract intent, domain, and keywords.

        Args:
            question: Natural language question

        Returns:
            Dictionary with:
            - intent: Classified intent
            - query_mode: Query mode for Phase 7 routing (find-method | explain-logic)
            - domain: Identified domain
            - keywords: List of key terms
            - confidence: Analysis confidence (0-1)
        """
        question_lower = question.lower()

        # Extract intent (legacy)
        intent = self._classify_intent(question_lower)

        # Phase 7: Extract query mode for routing
        query_mode, mode_confidence = self.classify_query_mode(question)

        # Extract domain
        domain, domain_confidence = self._identify_domain(question_lower)

        # Extract keywords
        keywords = self._extract_keywords(question)

        # Calculate overall confidence
        confidence = self._calculate_confidence(intent, domain, keywords, domain_confidence)

        result = {
            'intent': intent,
            'query_mode': query_mode,  # Phase 7: NEW
            'query_mode_confidence': mode_confidence,  # Phase 7: NEW
            'domain': domain,
            'keywords': keywords,
            'confidence': confidence,
            'question_length': len(question),
            'has_code_terms': self._has_code_terms(question_lower)
        }

        logger.info(f"Analyzed question: intent={intent}, query_mode={query_mode} ({mode_confidence:.2f}), "
                   f"domain={domain}, keywords={len(keywords)}, confidence={confidence:.2f}")

        return result

    def _classify_intent(self, question_lower: str) -> str:
        """Classify question intent using pattern matching."""
        intent_scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    score += 1
            intent_scores[intent] = score

        # Return intent with highest score, default to 'explain-concept'
        if not intent_scores or max(intent_scores.values()) == 0:
            return 'explain-concept'

        return max(intent_scores.items(), key=lambda x: x[1])[0]

    def classify_query_mode(self, question: str) -> Tuple[str, float]:
        """
        Classify query mode for Phase 7 routing.

        Routes between:
        - find-method: Simple method search by name (semantic mode - Phase 6)
        - explain-logic: Mechanism/flow explanation (control flow mode - Phase 7)

        Args:
            question: Natural language question

        Returns:
            Tuple of (query_mode, confidence)
            - query_mode: 'find-method' | 'explain-logic'
            - confidence: 0.0-1.0

        Examples:
            "What is timestamp2time_t?" → ("find-method", 0.9)
            "What mechanism ensures consistency during shutdown?" → ("explain-logic", 0.85)
        """
        question_lower = question.lower()

        # Count matches for each mode
        explain_logic_score = 0
        find_method_score = 0

        # Score explain-logic keywords
        for keyword in self.explain_logic_keywords:
            if keyword in question_lower:
                explain_logic_score += 1

        # Score find-method keywords
        for keyword in self.find_method_keywords:
            if keyword in question_lower:
                find_method_score += 1

        # Special patterns that strongly indicate explain-logic
        explain_logic_patterns = [
            r'\bmechanism\b.*\bensure',
            r'\bhow does.*\bhandle',
            r'\bwhat.*\bprocess.*\bmanage',
            r'\bduring\b.*\bshutdown',
            r'\bwhen\b.*\breceived',
            r'\bcoordinat\w*\b.*\bwith',
            r'\binteraction\b.*\bbetween',
            r'\bflow\b.*\bfrom.*\bto'
        ]

        for pattern in explain_logic_patterns:
            if re.search(pattern, question_lower):
                explain_logic_score += 2  # Strong signal

        # Special patterns that strongly indicate find-method
        find_method_patterns = [
            r'\bpurpose of\b.*\bfunction',
            r'\bwhat is\b.*\bmethod',
            r'\bwhat does\b.*\bfunction',
            r'\bfunction.*\bdo\b',
            r'\bmethod.*\bdo\b',
            r'\bdefined\s+in\b',
            r'\bfound\s+in\b'
        ]

        for pattern in find_method_patterns:
            if re.search(pattern, question_lower):
                find_method_score += 2  # Strong signal

        # Detect file:line references (strong find-method signal)
        if re.search(r'\b\w+\.c:\d+\b', question):
            find_method_score += 2

        # Determine query mode
        if explain_logic_score > find_method_score:
            query_mode = 'explain-logic'
            # Confidence based on score difference and absolute score
            score_diff = explain_logic_score - find_method_score
            confidence = min(0.5 + (score_diff * 0.1) + (explain_logic_score * 0.05), 1.0)
        elif find_method_score > explain_logic_score:
            query_mode = 'find-method'
            score_diff = find_method_score - explain_logic_score
            confidence = min(0.5 + (score_diff * 0.1) + (find_method_score * 0.05), 1.0)
        else:
            # Tie or no matches - use heuristics
            # Default to explain-logic if question is long and complex
            if len(question) > 80 or '?' in question[:-1]:  # Multiple clauses
                query_mode = 'explain-logic'
                confidence = 0.5
            else:
                query_mode = 'find-method'
                confidence = 0.5

        logger.debug(f"Query mode classification: {query_mode} (confidence={confidence:.2f}, "
                    f"explain_score={explain_logic_score}, find_score={find_method_score})")

        return query_mode, confidence

    def _identify_domain(self, question_lower: str) -> Tuple[str, float]:
        """
        Identify PostgreSQL domain.

        Returns:
            (domain, confidence)
        """
        domain_scores = {}

        for domain, keywords in self.domain_keywords.items():
            score = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword in question_lower:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                domain_scores[domain] = (score, matched_keywords)

        if not domain_scores:
            return 'general', 0.3

        # Get domain with highest score
        best_domain = max(domain_scores.items(), key=lambda x: x[1][0])
        domain_name = best_domain[0]
        score = best_domain[1][0]
        matched = best_domain[1][1]

        # Calculate confidence based on number of matched keywords
        confidence = min(0.5 + (score * 0.2), 1.0)

        logger.debug(f"Domain '{domain_name}' matched with keywords: {matched}")

        return domain_name, confidence

    def _extract_keywords(self, question: str) -> List[str]:
        """
        Extract important keywords from question.

        Extracts:
        - PostgreSQL-specific terms
        - Function names (camelCase, snake_case)
        - Technical terms
        """
        keywords = []

        # Extract camelCase and snake_case identifiers
        camel_case = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', question)
        snake_case = re.findall(r'\b[a-z]+_[a-z_]+\b', question)

        keywords.extend(camel_case)
        keywords.extend(snake_case)

        # Extract quoted terms
        quoted = re.findall(r'["\']([^"\']+)["\']', question)
        keywords.extend(quoted)

        # Extract uppercase terms (acronyms)
        uppercase = re.findall(r'\b[A-Z]{2,}\b', question)
        keywords.extend(uppercase)

        # Extract PostgreSQL-specific terms from domain keywords
        question_lower = question.lower()
        for domain, domain_keywords in self.domain_keywords.items():
            for keyword in domain_keywords:
                if keyword in question_lower and keyword not in keywords:
                    keywords.append(keyword)

        # Remove duplicates and empty strings
        keywords = list(set(k for k in keywords if k.strip()))

        # Limit to top 10 keywords
        return keywords[:10]

    def _has_code_terms(self, question_lower: str) -> bool:
        """Check if question contains code-related terms."""
        code_terms = [
            'function', 'method', 'call', 'struct', 'class',
            'pointer', 'memory', 'buffer', 'array', 'loop',
            'variable', 'parameter', 'return', 'malloc', 'free'
        ]

        return any(term in question_lower for term in code_terms)

    def _calculate_confidence(
        self,
        intent: str,
        domain: str,
        keywords: List[str],
        domain_confidence: float
    ) -> float:
        """
        Calculate overall analysis confidence.

        Factors:
        - Domain confidence (primary)
        - Number of keywords extracted
        - Intent classification certainty
        """
        # Base confidence from domain
        confidence = domain_confidence * 0.6

        # Add confidence from keywords (more keywords = higher confidence)
        keyword_confidence = min(len(keywords) * 0.05, 0.3)
        confidence += keyword_confidence

        # Add confidence from intent (if not default)
        if intent != 'explain-concept':
            confidence += 0.1

        return min(confidence, 1.0)

    def analyze_with_llm(self, question: str) -> Dict:
        """
        Advanced analysis using LLM.

        Falls back to rule-based analysis if LLM not available.

        Week 5: Now uses domain-adaptive prompts from PromptRegistry.
        """
        if self.llm is None:
            logger.debug("LLM not available, using rule-based analysis")
            return self.analyze(question)

        # Week 5: Build domain-adaptive prompt for LLM analysis
        # Use domain-specific analyst title instead of hardcoded "PostgreSQL"
        prompt = f"""Analyze this code analysis question and extract structured information.

You are an expert {self.code_analyst_title}.

Question: {question}

Extract:
1. Intent: find-function | explain-concept | security-check | code-analysis
2. Domain: vacuum | wal | mvcc | query-planning | memory | replication | storage | indexes | locking | parallel | partition | jsonb | security | background | extension | performance | general
3. Keywords: 3-5 key terms for retrieval

Output JSON:
{{"intent": "...", "domain": "...", "keywords": [...]}}
"""

        try:
            # Generate with LLM
            response = self.llm.generate_simple(
                prompt=prompt,
                max_tokens=150,
                temperature=0.3
            )

            # Parse JSON response
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group(0))

                # Add confidence and metadata
                result['confidence'] = 0.8  # Higher confidence with LLM
                result['question_length'] = len(question)
                result['has_code_terms'] = self._has_code_terms(question.lower())
                result['analysis_method'] = 'llm'

                logger.info(f"LLM analysis: intent={result['intent']}, "
                           f"domain={result['domain']}")

                return result
            else:
                logger.warning("Failed to parse LLM response, using rule-based fallback")
                return self.analyze(question)

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self.analyze(question)

    def batch_analyze(self, questions: List[str]) -> List[Dict]:
        """
        Analyze multiple questions efficiently.

        Args:
            questions: List of questions

        Returns:
            List of analysis results
        """
        results = []

        for question in questions:
            result = self.analyze(question)
            results.append(result)

        logger.info(f"Batch analyzed {len(questions)} questions")

        return results

    def get_domain_filter(self, domain: str) -> Dict:
        """
        Get ChromaDB filter for domain-specific retrieval.

        Args:
            domain: Identified domain

        Returns:
            Filter dict for ChromaDB where clause
        """
        if domain == 'general':
            return {}  # No filter for general questions

        # Map domain to topics that might be in metadata (Phase 2: Enhanced)
        domain_topics = {
            'vacuum': ['autovacuum', 'vacuum', 'maintenance', 'bloat'],
            'wal': ['wal', 'recovery', 'replication', 'xlog', 'checkpoint'],
            'mvcc': ['transaction', 'concurrency', 'isolation', 'snapshot', 'visibility'],
            'query-planning': ['planner', 'optimizer', 'execution', 'cost'],
            'memory': ['memory', 'buffer', 'cache', 'palloc', 'shmem'],
            'replication': ['replication', 'standby', 'streaming', 'slot'],
            'storage': ['heap', 'toast', 'page', 'tuple', 'relation'],
            'indexes': ['index', 'btree', 'access-method', 'scan'],
            'locking': ['lock', 'deadlock', 'lwlock', 'spinlock'],
            'parallel': ['parallel', 'worker', 'background', 'gather'],
            'executor': ['executor', 'execution', 'scan', 'join'],
            'catalog': ['catalog', 'metadata', 'schema', 'system-table'],
            'error-handling': ['error', 'exception', 'elog'],
            'networking': ['connection', 'socket', 'network'],
            'timestamp': ['timestamp', 'time', 'date']
        }

        topics = domain_topics.get(domain, [domain])

        # ChromaDB where filter (if topics field exists in metadata)
        # Note: This is a suggestion - actual implementation depends on metadata structure
        return {'topics': {'$in': topics}} if topics else {}
