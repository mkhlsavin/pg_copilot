"""Retriever Agent - Retrieves relevant context from ChromaDB."""
import logging
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

from src.retrieval.retrieval_cache import RetrievalCache

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """
    Retriever Agent for RAG context retrieval.

    Uses:
    - Analyzer Agent for question understanding
    - ChromaDB for semantic search
    """

    def __init__(
        self,
        vector_store,
        analyzer_agent,
        cache_size: int = 128,
        cache_ttl_seconds: Optional[float] = None,
        enable_cache_metrics: bool = True
    ):
        """
        Initialize Retriever Agent.

        Args:
            vector_store: VectorStoreReal instance
            analyzer_agent: AnalyzerAgent instance
            cache_size: Maximum number of cached retrieval entries
            cache_ttl_seconds: Time-to-live for cache entries (None = no expiration)
            enable_cache_metrics: Whether to collect detailed cache metrics
        """
        self.vector_store = vector_store
        self.analyzer = analyzer_agent

        # Initialize enhanced cache
        self._cache = RetrievalCache(
            max_size=cache_size,
            ttl_seconds=cache_ttl_seconds,
            enable_metrics=enable_cache_metrics,
            name="retriever_cache"
        )

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

        # Try cache
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            metrics = self._cache.get_metrics()
            logger.info(
                "Retrieval cache hit (rate=%.2f%%, size=%d/%d)",
                metrics['hit_rate'] * 100,
                len(self._cache),
                self._cache.max_size
            )
            cached_result.setdefault('retrieval_stats', {})['cache_hit'] = True
            return cached_result

        # Cache miss
        metrics = self._cache.get_metrics()
        logger.info(
            "Retrieving context for domain='%s', intent='%s' (cache miss, rate=%.2f%%)",
            analysis['domain'],
            analysis['intent'],
            metrics['miss_rate'] * 100
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

        # Store in cache
        self._cache.set(cache_key, result)

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
        - Tag relevance (NEW for RAGAS improvement)
        """
        if not examples or len(examples) <= top_k:
            return examples

        intent = analysis.get('intent', 'explain-concept')
        domain = analysis.get('domain', 'general')
        keywords = analysis.get('keywords', [])

        # Score each example
        scored_examples = []

        for example in examples:
            score = example['similarity']  # Base score

            # ENHANCEMENT: Boost if example contains domain-relevant tags
            # This addresses the low CPGQL similarity issue from RAGAS evaluation
            query_text = example.get('query', '')
            description = example.get('description', '')

            # Domain matching boost
            if domain != 'general' and domain in query_text.lower():
                score *= 1.3
                logger.debug(f"Domain boost for '{domain}' in example")

            # Keyword matching boost
            keyword_matches = sum(1 for kw in keywords if kw.lower() in query_text.lower() or kw.lower() in description.lower())
            if keyword_matches > 0:
                score *= (1.0 + 0.1 * keyword_matches)  # +10% per keyword match
                logger.debug(f"Keyword boost: {keyword_matches} matches")

            # Tag-based pattern matching boost
            # If example uses tag-based filtering, boost it
            if '.tag.' in query_text or 'tag.nameExact' in query_text:
                score *= 1.2
                logger.debug("Tag-based query boost")

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

    def retrieve_with_enrichment(
        self,
        question: str,
        analysis: Dict,
        enrichment_hints: Dict,
        top_k_qa: int = 3,
        top_k_cpgql: int = 10,
        final_k_cpgql: int = 5
    ) -> Dict:
        """
        Hybrid retrieval combining semantic search with enrichment-based filtering.

        This addresses the low CPGQL similarity issue (0.031-0.278) identified in RAGAS evaluation.
        Strategy: Over-fetch, then rerank using enrichment tags, domain, and keywords.

        Args:
            question: Natural language question
            analysis: Question analysis
            enrichment_hints: Enrichment hints with tags, domains, concepts
            top_k_qa: Q&A pairs to retrieve
            top_k_cpgql: Initial CPGQL examples to fetch (more than final)
            final_k_cpgql: Final CPGQL examples to return after reranking

        Returns:
            Retrieval results with enrichment-boosted CPGQL examples
        """
        # Over-fetch CPGQL examples for better reranking
        context = self.retrieve(
            question=question,
            analysis=analysis,
            top_k_qa=top_k_qa,
            top_k_cpgql=top_k_cpgql
        )

        # Enhanced reranking with enrichment hints
        enhanced_examples = self._rerank_with_enrichment(
            examples=context['cpgql_examples'],
            analysis=analysis,
            enrichment_hints=enrichment_hints,
            top_k=final_k_cpgql
        )

        context['cpgql_examples'] = enhanced_examples
        context['retrieval_stats']['enrichment_reranking'] = True

        logger.info(
            "Enrichment-based reranking: %d → %d examples (avg sim boost expected)",
            top_k_cpgql,
            final_k_cpgql
        )

        return context

    def _rerank_with_enrichment(
        self,
        examples: List[Dict],
        analysis: Dict,
        enrichment_hints: Dict,
        top_k: int
    ) -> List[Dict]:
        """
        Rerank CPGQL examples using enrichment tags and hints.

        Scoring strategy:
        1. Base semantic similarity
        2. Domain/subsystem match boost (+30%)
        3. Tag pattern match boost (+20%)
        4. Function purpose match boost (+15%)
        5. Data structure match boost (+15%)
        6. Feature match boost (+10%)
        """
        if not examples or len(examples) <= top_k:
            return examples

        # Extract enrichment data
        subsystems = set(enrichment_hints.get('subsystems', []))
        function_purposes = set(enrichment_hints.get('function_purposes', []))
        data_structures = set(enrichment_hints.get('data_structures', []))
        domain_concepts = set(enrichment_hints.get('domain_concepts', []))
        features = set(enrichment_hints.get('features', []))

        scored_examples = []

        for example in examples:
            score = example['similarity']  # Base score
            query_text = example.get('query', '').lower()
            description = example.get('description', '').lower()

            # Subsystem/domain boost
            for subsystem in subsystems:
                if subsystem.lower() in query_text or subsystem.lower() in description:
                    score *= 1.3
                    logger.debug(f"Subsystem boost: {subsystem}")
                    break

            # Function purpose boost
            for purpose in function_purposes:
                if purpose.lower() in query_text or purpose.lower() in description:
                    score *= 1.15
                    logger.debug(f"Purpose boost: {purpose}")
                    break

            # Data structure boost
            for ds in data_structures:
                if ds.lower() in query_text or ds.lower() in description:
                    score *= 1.15
                    logger.debug(f"Data structure boost: {ds}")
                    break

            # Domain concept boost
            for concept in domain_concepts:
                if concept.lower() in query_text or concept.lower() in description:
                    score *= 1.2
                    logger.debug(f"Concept boost: {concept}")
                    break

            # Feature boost
            for feature in features:
                if feature.lower() in query_text or feature.lower() in description:
                    score *= 1.1
                    logger.debug(f"Feature boost: {feature}")
                    break

            # Tag-based query pattern boost
            if '.tag.' in query_text or 'tag.nameExact' in query_text:
                score *= 1.2
                logger.debug("Tag-based pattern boost")

            scored_examples.append((score, example))

        # Sort by enriched score
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

    def get_cache_metrics(self) -> Dict:
        """
        Get comprehensive cache metrics.

        Returns:
            Dictionary with cache metrics including:
            - hit_rate: Cache hit rate (0-1)
            - miss_rate: Cache miss rate (0-1)
            - current_size: Number of cached entries
            - memory_bytes: Approximate memory usage
            - utilization: Cache utilization (0-1)
            - And more...
        """
        return self._cache.get_metrics()

    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            pattern: Optional pattern to match (e.g., "memory", "vacuum")
                    If None, clears all cache

        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            return self._cache.invalidate_all()
        else:
            # Invalidate by question pattern (index 0 in cache key)
            return self._cache.invalidate_pattern(pattern, key_index=0)

    def warm_cache(self, questions: List[str], top_k_qa: int = 3, top_k_cpgql: int = 5) -> int:
        """
        Warm cache with pre-computed retrievals for common questions.

        Args:
            questions: List of questions to pre-load
            top_k_qa: Number of Q&A pairs per question
            top_k_cpgql: Number of CPGQL examples per question

        Returns:
            Number of questions successfully cached
        """
        logger.info(f"Warming cache with {len(questions)} questions...")
        count = 0

        for question in questions:
            try:
                # Retrieve and cache
                self.retrieve(
                    question=question,
                    top_k_qa=top_k_qa,
                    top_k_cpgql=top_k_cpgql
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for question '{question[:50]}...': {e}")

        logger.info(f"Cache warmed: {count}/{len(questions)} questions cached")
        return count

    def export_cache_metrics(self, file_path: Optional[Path] = None) -> Dict:
        """
        Export cache metrics to JSON file.

        Args:
            file_path: Path to save metrics (optional)

        Returns:
            Metrics dictionary
        """
        return self._cache.export_metrics(file_path)

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
