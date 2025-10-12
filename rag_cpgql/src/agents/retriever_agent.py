"""Retriever Agent - Retrieves relevant context from ChromaDB."""
import logging
from collections import OrderedDict
from typing import Dict, List, Tuple, Any
from copy import deepcopy
from pathlib import Path

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """
    Retriever Agent for RAG context retrieval.

    Uses:
    - Analyzer Agent for question understanding
    - ChromaDB for semantic search
    """

    def __init__(self, vector_store, analyzer_agent, cache_size: int = 128):
        """
        Initialize Retriever Agent.

        Args:
            vector_store: VectorStoreReal instance
            analyzer_agent: AnalyzerAgent instance
            cache_size: Maximum number of cached retrieval entries
        """
        self.vector_store = vector_store
        self.analyzer = analyzer_agent
        self._cache_size = max(cache_size, 0)
        self._cache: "OrderedDict[Tuple[Any, ...], Dict]" = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    def retrieve(
        self,
        question: str,
        analysis: Dict = None,
        top_k_qa: int = 3,
        top_k_cpgql: int = 5
    ) -> Dict:
        """
        Retrieve relevant context for question.

        Args:
            question: Natural language question
            analysis: Optional pre-computed analysis from AnalyzerAgent
            top_k_qa: Number of Q&A pairs to retrieve
            top_k_cpgql: Number of CPGQL examples to retrieve

        Returns:
            Dictionary with:
            - similar_qa: List of similar Q&A pairs
            - cpgql_examples: List of CPGQL examples
            - analysis: Question analysis
            - retrieval_stats: Statistics
        """
        # Analyze question if not provided
        if analysis is None:
            analysis = self.analyzer.analyze(question)

        cache_key = self._make_cache_key(
            question=question,
            analysis=analysis,
            top_k_qa=top_k_qa,
            top_k_cpgql=top_k_cpgql
        )

        if self._cache_size > 0 and cache_key in self._cache:
            self._cache_hits += 1
            logger.info(
                "Retrieval cache hit (hits=%d, misses=%d)",
                self._cache_hits,
                self._cache_misses
            )
            # Move entry to the end to preserve LRU ordering
            self._cache.move_to_end(cache_key)
            cached_result = deepcopy(self._cache[cache_key])
            cached_result.setdefault('retrieval_stats', {})['cache_hit'] = True
            return cached_result

        self._cache_misses += 1
        logger.info(
            "Retrieving context for domain='%s', intent='%s' (cache miss #%d)",
            analysis['domain'],
            analysis['intent'],
            self._cache_misses
        )

        # Get domain filter for Q&A retrieval
        domain_filter = self._build_domain_filter(analysis['domain'])

        # Retrieve similar Q&A pairs
        similar_qa = self.vector_store.retrieve_qa(
            query=question,
            top_k=top_k_qa,
            filter_dict=domain_filter if domain_filter else None
        )

        # Retrieve CPGQL examples (with keywords for better relevance)
        cpgql_examples = self.vector_store.retrieve_cpgql(
            query=question,
            keywords=analysis.get('keywords', []),
            top_k=top_k_cpgql
        )

        # Calculate retrieval statistics
        stats = {
            'qa_retrieved': len(similar_qa),
            'cpgql_retrieved': len(cpgql_examples),
            'avg_qa_similarity': sum(q['similarity'] for q in similar_qa) / len(similar_qa) if similar_qa else 0,
            'avg_cpgql_similarity': sum(c['similarity'] for c in cpgql_examples) / len(cpgql_examples) if cpgql_examples else 0,
            'domain_filtered': bool(domain_filter),
            'cache_hit': False
        }

        logger.info(
            "Retrieved %d Q&A pairs (avg sim: %.3f), %d CPGQL examples (avg sim: %.3f)",
            stats['qa_retrieved'],
            stats['avg_qa_similarity'],
            stats['cpgql_retrieved'],
            stats['avg_cpgql_similarity']
        )

        result = {
            'similar_qa': similar_qa,
            'cpgql_examples': cpgql_examples,
            'analysis': analysis,
            'retrieval_stats': stats
        }

        if self._cache_size > 0:
            if len(self._cache) >= self._cache_size:
                self._cache.popitem(last=False)
            self._cache[cache_key] = deepcopy(result)

        return result

    def retrieve_with_reranking(
        self,
        question: str,
        analysis: Dict = None,
        top_k_qa: int = 5,
        top_k_cpgql: int = 10,
        final_k_qa: int = 3,
        final_k_cpgql: int = 5
    ) -> Dict:
        """
        Retrieve with over-fetching and reranking.

        Fetches more results than needed, then reranks based on:
        - Semantic similarity
        - Domain relevance
        - Question intent alignment

        Args:
            question: Natural language question
            analysis: Optional pre-computed analysis
            top_k_qa: Initial Q&A pairs to fetch
            top_k_cpgql: Initial CPGQL examples to fetch
            final_k_qa: Final Q&A pairs to return
            final_k_cpgql: Final CPGQL examples to return

        Returns:
            Same format as retrieve() but with reranked results
        """
        # Initial retrieval with higher k
        context = self.retrieve(
            question=question,
            analysis=analysis,
            top_k_qa=top_k_qa,
            top_k_cpgql=top_k_cpgql
        )

        # Rerank Q&A pairs
        reranked_qa = self._rerank_qa(
            context['similar_qa'],
            context['analysis'],
            final_k_qa
        )

        # Rerank CPGQL examples
        reranked_cpgql = self._rerank_cpgql(
            context['cpgql_examples'],
            context['analysis'],
            final_k_cpgql
        )

        # Update context with reranked results
        context['similar_qa'] = reranked_qa
        context['cpgql_examples'] = reranked_cpgql
        context['retrieval_stats']['reranked'] = True

        logger.info(f"Reranked to top-{final_k_qa} Q&A and top-{final_k_cpgql} CPGQL")

        return context

    def _build_domain_filter(self, domain: str) -> Dict:
        """Build ChromaDB filter for domain-specific retrieval."""
        # Note: Filtering depends on metadata structure
        # Current implementation: no filtering as metadata may not have domain field
        # Future: Add domain field to metadata during indexing

        # For now, return empty filter (no filtering)
        # TODO: Enhance metadata with domain classification during indexing
        return {}

    def _rerank_qa(
        self,
        qa_pairs: List[Dict],
        analysis: Dict,
        top_k: int
    ) -> List[Dict]:
        """
        Rerank Q&A pairs based on analysis.

        Scoring factors:
        - Semantic similarity (already in data)
        - Difficulty match (if available)
        - Source match (prefer certain sources)
        """
        if not qa_pairs or len(qa_pairs) <= top_k:
            return qa_pairs

        # Score each Q&A pair
        scored_qa = []

        for qa in qa_pairs:
            score = qa['similarity']  # Base score from semantic similarity

            # Boost score if difficulty matches expected complexity
            # (More sophisticated reranking can be added here)

            # Boost if source is high quality
            if qa.get('source') in ['official-docs', 'postgresql-docs']:
                score *= 1.1

            scored_qa.append((score, qa))

        # Sort by score and return top-k
        scored_qa.sort(key=lambda x: x[0], reverse=True)

        return [qa for _, qa in scored_qa[:top_k]]

    def _rerank_cpgql(
        self,
        examples: List[Dict],
        analysis: Dict,
        top_k: int
    ) -> List[Dict]:
        """
        Rerank CPGQL examples based on analysis.

        Scoring factors:
        - Semantic similarity
        - Complexity match
        - Category relevance
        """
        if not examples or len(examples) <= top_k:
            return examples

        intent = analysis.get('intent', 'explain-concept')

        # Score each example
        scored_examples = []

        for example in examples:
            score = example['similarity']  # Base score

            # Boost if category matches intent
            category = example.get('category', '')

            if intent == 'find-function' and 'method' in category.lower():
                score *= 1.2
            elif intent == 'security-check' and 'security' in category.lower():
                score *= 1.2

            # Boost if complexity matches
            # (Simple questions prefer simple examples)
            complexity = example.get('complexity', 'unknown')
            question_length = analysis.get('question_length', 0)

            if question_length < 50 and complexity == 'simple':
                score *= 1.1
            elif question_length > 100 and complexity == 'complex':
                score *= 1.1

            scored_examples.append((score, example))

        # Sort by score and return top-k
        scored_examples.sort(key=lambda x: x[0], reverse=True)

        return [ex for _, ex in scored_examples[:top_k]]

    def retrieve_by_keywords(
        self,
        keywords: List[str],
        top_k: int = 5
    ) -> Dict:
        """
        Retrieve examples based on keywords only.

        Useful for targeted retrieval when specific terms are known.

        Args:
            keywords: List of keywords
            top_k: Number of results

        Returns:
            Dictionary with Q&A and CPGQL results
        """
        query = ' '.join(keywords)

        similar_qa = self.vector_store.retrieve_qa(
            query=query,
            top_k=top_k
        )

        cpgql_examples = self.vector_store.retrieve_cpgql(
            query=query,
            keywords=keywords,
            top_k=top_k
        )

        return {
            'similar_qa': similar_qa,
            'cpgql_examples': cpgql_examples,
            'query': query
        }

    def get_stats(self) -> Dict:
        """Get retrieval statistics from vector store."""
        return self.vector_store.get_stats()

    def _make_cache_key(
        self,
        question: str,
        analysis: Dict,
        top_k_qa: int,
        top_k_cpgql: int
    ) -> Tuple[Any, ...]:
        """Build cache key from normalized inputs for retrieval caching."""
        normalized_question = question.strip()
        domain = analysis.get('domain')
        intent = analysis.get('intent')
        keywords = tuple(sorted(analysis.get('keywords', [])))

        return (
            normalized_question,
            domain,
            intent,
            keywords,
            top_k_qa,
            top_k_cpgql
        )
