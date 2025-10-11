"""Enhanced RAG-CPGQL pipeline with grammar-constrained generation."""
import logging
from typing import Dict, List, Optional
from pathlib import Path

from retrieval.vector_store import VectorStore
from generation.llm_interface import LLMInterface
from generation.cpgql_generator import CPGQLGenerator
from generation.prompts import build_cpgql_generation_prompt, build_interpretation_prompt
from execution.joern_client import JoernClient
from execution.query_validator import QueryValidator
from evaluation.metrics import Evaluator

logger = logging.getLogger(__name__)


class RAGCPGQLPipelineGrammar:
    """
    Enhanced RAG-CPGQL pipeline with grammar-constrained query generation.

    Key improvements over base pipeline:
    - Grammar-constrained generation (100% valid queries)
    - LLMxCPG-Q model (fine-tuned for CPGQL)
    - Enrichment hints from retrieved examples
    - Post-processing cleanup
    """

    def __init__(
        self,
        llm: LLMInterface,
        vector_store: VectorStore,
        joern_client: JoernClient,
        top_k_qa: int = 3,
        top_k_cpgql: int = 5,
        use_grammar: bool = True,
        use_enrichment: bool = True
    ):
        """
        Initialize enhanced RAG pipeline.

        Args:
            llm: LLM interface (should use LLMxCPG-Q)
            vector_store: Vector store for retrieval
            joern_client: Joern HTTP client
            top_k_qa: Top-k Q&A pairs to retrieve
            top_k_cpgql: Top-k CPGQL examples to retrieve
            use_grammar: Enable grammar constraints (recommended)
            use_enrichment: Use enrichment hints from retrieved examples
        """
        self.llm = llm
        self.vector_store = vector_store
        self.joern = joern_client
        self.validator = QueryValidator()
        self.evaluator = Evaluator()
        self.top_k_qa = top_k_qa
        self.top_k_cpgql = top_k_cpgql
        self.use_enrichment = use_enrichment

        # Initialize grammar-constrained generator
        self.cpgql_generator = CPGQLGenerator(llm, use_grammar=use_grammar)

        logger.info("=" * 80)
        logger.info("Enhanced RAG-CPGQL Pipeline Initialized")
        logger.info("=" * 80)
        logger.info(f"Grammar constraints: {'ENABLED' if self.cpgql_generator.use_grammar else 'DISABLED'}")
        logger.info(f"Enrichment hints:    {'ENABLED' if use_enrichment else 'DISABLED'}")
        logger.info(f"Model:               LLMxCPG-Q (fine-tuned for CPGQL)")
        logger.info(f"Top-k Q&A:           {top_k_qa}")
        logger.info(f"Top-k CPGQL:         {top_k_cpgql}")
        logger.info("=" * 80)

    def extract_enrichment_hints(
        self,
        question: str,
        similar_qa: List[Dict],
        cpgql_examples: List[Dict]
    ) -> str:
        """
        Extract enrichment hints from retrieved examples.

        Args:
            question: User question
            similar_qa: Retrieved similar Q&A pairs
            cpgql_examples: Retrieved CPGQL examples

        Returns:
            Enrichment hints string
        """
        if not self.use_enrichment:
            return None

        hints = []

        # Extract from CPGQL examples
        if cpgql_examples:
            hints.append("Relevant CPGQL patterns:")
            for i, ex in enumerate(cpgql_examples[:3], 1):
                query = ex.get('query', '')
                desc = ex.get('description', '')
                if query:
                    hints.append(f"  {i}. {desc}: {query}")

        # Extract from Q&A pairs (look for code mentions)
        code_mentions = set()
        for qa in similar_qa[:3]:
            answer = qa.get('answer', '')
            # Simple extraction: look for function names, file names
            import re
            # Find function names (word followed by parentheses)
            funcs = re.findall(r'\b(\w+)\s*\(', answer)
            code_mentions.update(funcs[:2])  # Top 2 per answer

        if code_mentions:
            hints.append("\nMentioned functions/methods:")
            for func in list(code_mentions)[:5]:
                hints.append(f"  - {func}()")

        return "\n".join(hints) if hints else None

    def generate_cpgql_query(self, question: str) -> tuple:
        """
        Generate CPGQL query using grammar-constrained RAG.

        Args:
            question: User question

        Returns:
            Tuple of (query_string, is_valid, error_message)
        """
        logger.info(f"Generating CPGQL query for: {question[:80]}...")

        # 1. Retrieve similar Q&A pairs
        similar_qa = self.vector_store.search_similar_qa(question, k=self.top_k_qa)
        logger.debug(f"Retrieved {len(similar_qa)} similar Q&A pairs")

        # 2. Retrieve similar CPGQL examples
        cpgql_examples = self.vector_store.search_similar_cpgql(question, k=self.top_k_cpgql)
        logger.debug(f"Retrieved {len(cpgql_examples)} CPGQL examples")

        # 3. Extract enrichment hints
        enrichment_hints = self.extract_enrichment_hints(
            question, similar_qa, cpgql_examples
        )

        if enrichment_hints:
            logger.debug(f"Enrichment hints:\n{enrichment_hints}")

        # 4. Generate query with grammar constraints
        query = self.cpgql_generator.generate_query(
            question=question,
            enrichment_hints=enrichment_hints,
            max_tokens=400,
            temperature=0.5  # Lower for more deterministic
        )

        logger.debug(f"Generated query: {query}")

        # 5. Validate
        is_valid, error_message = self.cpgql_generator.validate_query(query)

        if is_valid:
            logger.info(f"✅ Valid query: {query}")
        else:
            logger.warning(f"❌ Invalid query: {error_message}")

        return query, is_valid, error_message

    def execute_query(self, query: str) -> Dict:
        """
        Execute CPGQL query via Joern.

        Args:
            query: CPGQL query string

        Returns:
            Execution result dictionary
        """
        logger.info(f"Executing query: {query[:80]}...")
        return self.joern.execute_query(query)

    def interpret_results(
        self,
        question: str,
        query: str,
        exec_result: Dict
    ) -> str:
        """
        Interpret Joern results into natural language answer.

        Args:
            question: Original question
            query: CPGQL query that was executed
            exec_result: Joern execution result

        Returns:
            Natural language answer
        """
        if not exec_result.get('success'):
            return f"Query execution failed: {exec_result.get('error', 'Unknown error')}"

        logger.info("Interpreting query results...")

        # Build interpretation prompt
        system_prompt, user_prompt = build_interpretation_prompt(
            question, query, exec_result.get('results', {})
        )

        # Generate interpretation
        answer = self.llm.generate(
            system_prompt,
            user_prompt,
            max_tokens=512,
            temperature=0.7
        )

        logger.debug(f"Generated answer: {answer[:150]}...")
        return answer

    def run_full_pipeline(self, question: str, reference_answer: str = None) -> Dict:
        """
        Run complete grammar-enhanced RAG-CPGQL pipeline.

        Args:
            question: User question
            reference_answer: Reference answer for evaluation (optional)

        Returns:
            Dictionary with all results and metrics
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"Running Grammar-Enhanced Pipeline")
        logger.info(f"Question: {question}")
        logger.info("=" * 80)

        result = {
            'question': question,
            'reference_answer': reference_answer,
            'grammar_enabled': self.cpgql_generator.use_grammar,
            'enrichment_enabled': self.use_enrichment
        }

        # 1. Generate CPGQL query (with grammar + enrichment)
        query, is_valid, validation_msg = self.generate_cpgql_query(question)
        result['cpgql_query'] = query
        result['query_valid'] = is_valid
        result['validation_message'] = validation_msg

        if not is_valid:
            result['generated_answer'] = None
            result['execution_result'] = {'success': False, 'error': validation_msg}
            if reference_answer:
                result['metrics'] = self.evaluator.evaluate_single(
                    question, "", reference_answer, query,
                    result['execution_result']
                )
            return result

        # 2. Execute query
        exec_result = self.execute_query(query)
        result['execution_result'] = exec_result

        # 3. Interpret results
        if exec_result.get('success'):
            answer = self.interpret_results(question, query, exec_result)
            result['generated_answer'] = answer
        else:
            result['generated_answer'] = None

        # 4. Evaluate (if reference answer provided)
        if reference_answer:
            result['metrics'] = self.evaluator.evaluate_single(
                question,
                result.get('generated_answer', ''),
                reference_answer,
                query,
                exec_result
            )

        logger.info("Pipeline execution complete")
        logger.info("=" * 80 + "\n")
        return result

    def run_batch(self, qa_pairs: List[Dict], save_path: Optional[Path] = None) -> Dict:
        """
        Run pipeline on batch of Q&A pairs.

        Args:
            qa_pairs: List of Q&A dictionaries
            save_path: Optional path to save results

        Returns:
            Dictionary with results and aggregate metrics
        """
        results = []

        logger.info("\n" + "=" * 80)
        logger.info(f"BATCH PROCESSING: {len(qa_pairs)} questions")
        logger.info("=" * 80 + "\n")

        for i, qa in enumerate(qa_pairs, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing {i}/{len(qa_pairs)}")
            logger.info(f"{'=' * 80}\n")

            result = self.run_full_pipeline(
                qa['question'],
                qa.get('answer')
            )

            # Add metadata
            result['qa_index'] = i - 1
            result['difficulty'] = qa.get('difficulty')
            result['topics'] = qa.get('topics', [])

            results.append(result)

        # Compute aggregate statistics
        stats = self._compute_batch_stats(results)

        batch_result = {
            'total_questions': len(qa_pairs),
            'results': results,
            'statistics': stats,
            'pipeline_config': {
                'grammar_enabled': self.cpgql_generator.use_grammar,
                'enrichment_enabled': self.use_enrichment,
                'model': 'LLMxCPG-Q',
                'top_k_qa': self.top_k_qa,
                'top_k_cpgql': self.top_k_cpgql
            }
        }

        # Save results if path provided
        if save_path:
            import json
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, indent=2, ensure_ascii=False)
            logger.info(f"\n✅ Results saved to: {save_path}")

        # Print summary
        self._print_batch_summary(stats)

        return batch_result

    def _compute_batch_stats(self, results: List[Dict]) -> Dict:
        """Compute aggregate statistics from batch results."""
        total = len(results)
        valid_queries = sum(1 for r in results if r.get('query_valid'))
        successful_exec = sum(1 for r in results if r.get('execution_result', {}).get('success'))

        stats = {
            'total_questions': total,
            'valid_queries': valid_queries,
            'valid_query_rate': valid_queries / total if total > 0 else 0,
            'successful_executions': successful_exec,
            'execution_success_rate': successful_exec / total if total > 0 else 0
        }

        # Aggregate metrics if available
        if any('metrics' in r for r in results):
            metrics_list = [r['metrics'] for r in results if 'metrics' in r]
            if metrics_list:
                # Average semantic similarity
                if 'semantic_similarity' in metrics_list[0]:
                    avg_sim = sum(m['semantic_similarity'] for m in metrics_list) / len(metrics_list)
                    stats['avg_semantic_similarity'] = avg_sim

        return stats

    def _print_batch_summary(self, stats: Dict):
        """Print batch processing summary."""
        logger.info("\n" + "=" * 80)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total questions:        {stats['total_questions']}")
        logger.info(f"Valid queries:          {stats['valid_queries']}/{stats['total_questions']} ({stats['valid_query_rate']*100:.1f}%)")
        logger.info(f"Successful executions:  {stats['successful_executions']}/{stats['total_questions']} ({stats['execution_success_rate']*100:.1f}%)")

        if 'avg_semantic_similarity' in stats:
            logger.info(f"Avg semantic similarity: {stats['avg_semantic_similarity']:.3f}")

        logger.info("=" * 80 + "\n")
