"""Evaluation metrics for RAG-CPGQL system."""
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SemanticSimilarity:
    """Compute semantic similarity between texts."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize similarity calculator.

        Args:
            model_name: Sentence transformer model name
        """
        self.encoder = SentenceTransformer(model_name)
        logger.info(f"Loaded similarity model: {model_name}")

    def compute(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        if not text1 or not text2:
            return 0.0

        emb1 = self.encoder.encode([text1])
        emb2 = self.encoder.encode([text2])
        return float(cosine_similarity(emb1, emb2)[0][0])


class EntityExtractor:
    """Extract code entities from text."""

    def __init__(self):
        """Initialize entity extractor."""
        # Common words to filter out
        self.stopwords = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from', 'into',
            'will', 'are', 'was', 'were', 'been', 'have', 'has', 'had',
            'does', 'did', 'can', 'could', 'should', 'would', 'may', 'might',
            'must', 'shall', 'when', 'where', 'what', 'which', 'who', 'how'
        }

    def extract_functions(self, text: str) -> set:
        """
        Extract function names from text.

        Args:
            text: Input text

        Returns:
            Set of function names
        """
        # PostgreSQL function patterns:
        # - lowercase_with_underscores (e.g., heap_insert, palloc)
        # - CamelCase (e.g., ExecInitNode, TransactionIdIsValid)
        patterns = [
            r'\b[a-z][a-z0-9_]*[a-z0-9]\b',  # lowercase_underscore
            r'\b[A-Z][a-zA-Z0-9]*\b'  # CamelCase
        ]

        functions = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            functions.update(matches)

        # Filter stopwords and short tokens
        functions = {
            f for f in functions
            if f.lower() not in self.stopwords and len(f) > 2
        }

        return functions

    def extract_files(self, text: str) -> set:
        """
        Extract file paths from text.

        Args:
            text: Input text

        Returns:
            Set of file paths
        """
        # Match file paths with .c or .h extensions
        pattern = r'[a-zA-Z_./][a-zA-Z0-9_./]*\.(c|h)'
        files = set(re.findall(pattern, text))
        return {f[0] for f in files}  # Extract just the filename with extension

    def extract_all(self, text: str) -> Dict[str, set]:
        """
        Extract all entities from text.

        Args:
            text: Input text

        Returns:
            Dictionary with 'functions' and 'files' sets
        """
        return {
            'functions': self.extract_functions(text),
            'files': self.extract_files(text)
        }


class EntityMetrics:
    """Compute precision, recall, F1 for entities."""

    def __init__(self):
        """Initialize entity metrics calculator."""
        self.extractor = EntityExtractor()

    def compute_precision_recall(
        self,
        generated: str,
        reference: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute precision, recall, F1 for entities.

        Args:
            generated: Generated answer text
            reference: Reference answer text

        Returns:
            Dictionary with metrics for each entity type
        """
        gen_entities = self.extractor.extract_all(generated)
        ref_entities = self.extractor.extract_all(reference)

        results = {}
        for entity_type in ['functions', 'files']:
            gen_set = gen_entities[entity_type]
            ref_set = ref_entities[entity_type]

            if len(gen_set) == 0 and len(ref_set) == 0:
                precision = recall = f1 = 1.0
            elif len(gen_set) == 0:
                precision = recall = f1 = 0.0
            else:
                intersection = gen_set & ref_set
                precision = len(intersection) / len(gen_set) if gen_set else 0
                recall = len(intersection) / len(ref_set) if ref_set else 0
                f1 = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0 else 0
                )

            results[entity_type] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'generated_count': len(gen_set),
                'reference_count': len(ref_set),
                'intersection_count': len(gen_set & ref_set)
            }

        return results


class Evaluator:
    """Main evaluator for RAG-CPGQL system."""

    def __init__(self):
        """Initialize evaluator with all metrics."""
        self.semantic_sim = SemanticSimilarity()
        self.entity_metrics = EntityMetrics()
        logger.info("Evaluator initialized")

    def evaluate_single(
        self,
        question: str,
        generated_answer: str,
        reference_answer: str,
        cpgql_query: str,
        execution_result: Dict
    ) -> Dict:
        """
        Evaluate a single Q&A pair.

        Args:
            question: Original question
            generated_answer: Generated answer
            reference_answer: Reference answer
            cpgql_query: Generated CPGQL query
            execution_result: Joern execution result

        Returns:
            Dictionary with all metrics
        """
        metrics = {
            'question': question,
        }

        # 1. Query validity
        metrics['query_valid'] = cpgql_query is not None and cpgql_query != ""

        # 2. Execution success
        metrics['execution_success'] = execution_result.get('success', False)

        # 3. Semantic similarity (if execution succeeded)
        if metrics['execution_success'] and generated_answer:
            metrics['semantic_similarity'] = self.semantic_sim.compute(
                generated_answer, reference_answer
            )
        else:
            metrics['semantic_similarity'] = 0.0

        # 4. Entity precision/recall
        entity_scores = self.entity_metrics.compute_precision_recall(
            generated_answer if generated_answer else "",
            reference_answer
        )
        metrics['entity_metrics'] = entity_scores

        # 5. Overall F1 (average of function and file F1)
        function_f1 = entity_scores['functions']['f1']
        file_f1 = entity_scores['files']['f1']
        metrics['overall_f1'] = (function_f1 + file_f1) / 2

        # 6. Error information (if applicable)
        if not metrics['execution_success']:
            metrics['error'] = execution_result.get('error', 'Unknown error')

        return metrics

    def evaluate_batch(self, results: List[Dict]) -> Dict:
        """
        Aggregate metrics across batch.

        Args:
            results: List of evaluation results from evaluate_single

        Returns:
            Aggregated metrics
        """
        total = len(results)

        if total == 0:
            return {}

        # Compute averages
        valid_queries = sum(1 for r in results if r.get('query_valid', False))
        successful_execs = sum(1 for r in results if r.get('execution_success', False))

        semantic_sims = [r['semantic_similarity'] for r in results]
        function_f1s = [r['entity_metrics']['functions']['f1'] for r in results]
        file_f1s = [r['entity_metrics']['files']['f1'] for r in results]
        overall_f1s = [r['overall_f1'] for r in results]

        return {
            'total_questions': total,
            'query_validity_rate': valid_queries / total,
            'execution_success_rate': successful_execs / total,
            'avg_semantic_similarity': np.mean(semantic_sims),
            'std_semantic_similarity': np.std(semantic_sims),
            'avg_function_f1': np.mean(function_f1s),
            'avg_file_f1': np.mean(file_f1s),
            'avg_overall_f1': np.mean(overall_f1s),
            'median_semantic_similarity': np.median(semantic_sims),
            'median_overall_f1': np.median(overall_f1s)
        }
