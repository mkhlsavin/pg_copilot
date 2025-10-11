"""Analyzer Agent - Extracts intent, domain, and keywords from questions."""
import logging
import json
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """
    Analyzer Agent for question understanding.

    Extracts:
    - Intent: find-function | explain-concept | security-check | code-analysis
    - Domain: vacuum | wal | mvcc | query-planning | memory | replication | etc.
    - Keywords: Key terms for retrieval
    """

    def __init__(self, llm=None):
        """
        Initialize Analyzer Agent.

        Args:
            llm: Optional LLM interface for advanced analysis
        """
        self.llm = llm

        # PostgreSQL domain keywords mapping
        self.domain_keywords = {
            'vacuum': ['vacuum', 'autovacuum', 'analyze', 'freeze', 'wraparound'],
            'wal': ['wal', 'write-ahead', 'log', 'checkpoint', 'recovery', 'replay'],
            'mvcc': ['mvcc', 'transaction', 'isolation', 'snapshot', 'visibility', 'xid'],
            'query-planning': ['planner', 'optimizer', 'execution', 'plan', 'cost', 'statistics'],
            'memory': ['shared_buffers', 'memory', 'cache', 'buffer', 'palloc', 'malloc'],
            'replication': ['replication', 'standby', 'primary', 'streaming', 'logical', 'physical'],
            'storage': ['heap', 'toast', 'page', 'tuple', 'relation', 'tablespace'],
            'indexes': ['btree', 'index', 'gin', 'gist', 'brin', 'hash', 'spgist'],
            'locking': ['lock', 'deadlock', 'lightweight', 'spinlock', 'lwlock', 'heavyweight'],
            'parallel': ['parallel', 'worker', 'background', 'gather', 'partition'],
            'partition': ['partition', 'partitioning', 'pruning', 'constraint'],
            'jsonb': ['jsonb', 'json', 'document', 'key-value'],
            'security': ['authentication', 'authorization', 'scram', 'password', 'role', 'grant'],
            'background': ['autovacuum', 'bgwriter', 'checkpointer', 'walwriter', 'archiver'],
            'extension': ['extension', 'hook', 'plugin', 'contrib'],
            'performance': ['performance', 'bottleneck', 'slow', 'optimization', 'tuning']
        }

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

    def analyze(self, question: str) -> Dict:
        """
        Analyze question to extract intent, domain, and keywords.

        Args:
            question: Natural language question

        Returns:
            Dictionary with:
            - intent: Classified intent
            - domain: Identified domain
            - keywords: List of key terms
            - confidence: Analysis confidence (0-1)
        """
        question_lower = question.lower()

        # Extract intent
        intent = self._classify_intent(question_lower)

        # Extract domain
        domain, domain_confidence = self._identify_domain(question_lower)

        # Extract keywords
        keywords = self._extract_keywords(question)

        # Calculate overall confidence
        confidence = self._calculate_confidence(intent, domain, keywords, domain_confidence)

        result = {
            'intent': intent,
            'domain': domain,
            'keywords': keywords,
            'confidence': confidence,
            'question_length': len(question),
            'has_code_terms': self._has_code_terms(question_lower)
        }

        logger.info(f"Analyzed question: intent={intent}, domain={domain}, "
                   f"keywords={len(keywords)}, confidence={confidence:.2f}")

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
        """
        if self.llm is None:
            logger.debug("LLM not available, using rule-based analysis")
            return self.analyze(question)

        # Build prompt for LLM analysis
        prompt = f"""Analyze this PostgreSQL question and extract structured information.

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

        # Map domain to topics that might be in metadata
        domain_topics = {
            'vacuum': ['autovacuum', 'vacuum', 'maintenance'],
            'wal': ['wal', 'recovery', 'replication'],
            'mvcc': ['transaction', 'concurrency', 'isolation'],
            'query-planning': ['planner', 'optimizer', 'execution'],
            'memory': ['memory', 'buffer', 'cache'],
            'indexes': ['index', 'btree', 'access-method']
        }

        topics = domain_topics.get(domain, [domain])

        # ChromaDB where filter (if topics field exists in metadata)
        # Note: This is a suggestion - actual implementation depends on metadata structure
        return {'topics': {'$in': topics}} if topics else {}
