"""Main RAG-CPGQL pipeline."""
import logging
from typing import Dict, List, Optional

from retrieval.vector_store import VectorStore
from generation.llm_interface import LLMInterface
from generation.prompts import build_cpgql_generation_prompt, build_interpretation_prompt
from execution.joern_client import JoernClient
from execution.query_validator import QueryValidator
from evaluation.metrics import Evaluator

logger = logging.getLogger(__name__)


class RAGCPGQLPipeline:
    """End-to-end RAG-CPGQL pipeline."""

    def __init__(
        self,
        llm: LLMInterface,
        vector_store: VectorStore,
        joern_client: JoernClient,
        top_k_qa: int = 3,
        top_k_cpgql: int = 5
    ):
        """
        Initialize RAG pipeline.

        Args:
            llm: LLM interface for generation
            vector_store: Vector store for retrieval
            joern_client: Joern HTTP client
            top_k_qa: Top-k Q&A pairs to retrieve
            top_k_cpgql: Top-k CPGQL examples to retrieve
        """
        self.llm = llm
        self.vector_store = vector_store
        self.joern = joern_client
        self.validator = QueryValidator()
        self.evaluator = Evaluator()
        self.top_k_qa = top_k_qa
        self.top_k_cpgql = top_k_cpgql

        logger.info("RAG-CPGQL pipeline initialized")

    def generate_cpgql_query(self, question: str) -> tuple:
        """
        Generate CPGQL query using RAG.

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

        # 3. Build prompt
        system_prompt, user_prompt = build_cpgql_generation_prompt(
            question, similar_qa, cpgql_examples
        )

        # 4. Generate query
        response = self.llm.generate(
            system_prompt,
            user_prompt,
            max_tokens=512,
            temperature=0.7
        )

        logger.debug(f"LLM response: {response[:200]}...")

        # 5. Validate and parse
        query, is_valid, message = self.validator.validate_and_parse(response)

        if is_valid:
            logger.info(f"Generated valid query: {query}")
        else:
            logger.warning(f"Query validation failed: {message}")

        return query, is_valid, message

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
        Run complete RAG-CPGQL pipeline for a question.

        Args:
            question: User question
            reference_answer: Reference answer for evaluation (optional)

        Returns:
            Dictionary with all results and metrics
        """
        logger.info("=" * 60)
        logger.info(f"Running pipeline for: {question}")
        logger.info("=" * 60)

        result = {
            'question': question,
            'reference_answer': reference_answer
        }

        # 1. Generate CPGQL query
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
        return result

    def run_batch(self, qa_pairs: List[Dict]) -> List[Dict]:
        """
        Run pipeline on batch of Q&A pairs.

        Args:
            qa_pairs: List of Q&A dictionaries

        Returns:
            List of result dictionaries
        """
        results = []

        for i, qa in enumerate(qa_pairs, 1):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing {i}/{len(qa_pairs)}")
            logger.info(f"{'=' * 60}\n")

            result = self.run_full_pipeline(
                qa['question'],
                qa.get('answer')
            )

            # Add original Q&A metadata
            result['qa_index'] = i - 1
            result['difficulty'] = qa.get('difficulty')
            result['topics'] = qa.get('topics', [])

            results.append(result)

        return results
