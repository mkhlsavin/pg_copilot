"""
Phase 1 Validation Test Suite

This script validates the impact of integrating code documentation (comments)
into the RAG-CPGQL pipeline by comparing answer quality with/without documentation.

Target: Improve answer quality from 10% baseline to 35% with documentation.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.generator_agent import GeneratorAgent
from src.agents.retriever_agent import RetrieverAgent
from src.execution.joern_client import JoernClient
from src.agents.enrichment_prompt_builder import EnrichmentPromptBuilder
from src.generation.cpgql_generator import CPGQLGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Test questions covering different PostgreSQL subsystems
TEST_QUESTIONS = [
    # Transaction and MVCC (5 questions)
    {
        "question": "How does PostgreSQL implement MVCC for transaction isolation?",
        "category": "transaction/mvcc",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL determine tuple visibility in a multi-version snapshot?",
        "category": "transaction/mvcc",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL handle transaction rollback and cleanup?",
        "category": "transaction/mvcc",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL prevent phantom reads in repeatable read isolation?",
        "category": "transaction/mvcc",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL implement two-phase commit for distributed transactions?",
        "category": "transaction/mvcc",
        "difficulty": "hard"
    },

    # Access methods and indexing (5 questions)
    {
        "question": "How does PostgreSQL's BRIN index work for range queries?",
        "category": "access/indexing",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL implement GIN index for full-text search?",
        "category": "access/indexing",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL maintain index consistency during concurrent updates?",
        "category": "access/indexing",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL perform index vacuum and cleanup?",
        "category": "access/indexing",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL choose between sequential and index scan?",
        "category": "access/indexing",
        "difficulty": "medium"
    },

    # Storage and buffer management (5 questions)
    {
        "question": "How does PostgreSQL manage the shared buffer pool?",
        "category": "storage/buffer",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL implement write-ahead logging (WAL)?",
        "category": "storage/buffer",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL handle page checksums for data corruption detection?",
        "category": "storage/buffer",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL implement heap tuple storage and organization?",
        "category": "storage/buffer",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL perform vacuum to reclaim dead tuple space?",
        "category": "storage/buffer",
        "difficulty": "hard"
    },

    # Catalog and ACL (5 questions)
    {
        "question": "How does PostgreSQL check access permissions using ACL?",
        "category": "catalog/acl",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL implement row-level security policies?",
        "category": "catalog/acl",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL manage system catalog updates during DDL?",
        "category": "catalog/acl",
        "difficulty": "hard"
    },
    {
        "question": "How does PostgreSQL handle large object access control?",
        "category": "catalog/acl",
        "difficulty": "medium"
    },
    {
        "question": "How does PostgreSQL prevent operations inside transaction blocks?",
        "category": "catalog/acl",
        "difficulty": "medium"
    }
]


class Phase1Validator:
    """Validate Phase 1 documentation integration impact."""

    def __init__(self, joern_host: str = "localhost:8080"):
        """Initialize validator.

        Args:
            joern_host: Joern server host:port
        """
        self.joern_client = JoernClient(joern_host)
        self.analyzer = AnalyzerAgent()
        self.retriever = RetrieverAgent()
        self.enrichment = EnrichmentAgent()

        # Create generator with CPGQL generator
        cpgql_generator = CPGQLGenerator()

        # Create generators with and without documentation
        self.generator_with_docs = GeneratorAgent(
            cpgql_generator=cpgql_generator,
            use_grammar=True,
            enable_feedback=False
        )
        self.generator_with_docs.enrichment_builder = EnrichmentPromptBuilder(enable_documentation=True)

        self.generator_without_docs = GeneratorAgent(
            cpgql_generator=cpgql_generator,
            use_grammar=True,
            enable_feedback=False
        )
        self.generator_without_docs.enrichment_builder = EnrichmentPromptBuilder(enable_documentation=False)

        logger.info("Phase1Validator initialized")
        logger.info(f"Documentation retriever WITH docs: {self.generator_with_docs.enrichment_builder.enable_documentation}")
        logger.info(f"Documentation retriever WITHOUT docs: {self.generator_without_docs.enrichment_builder.enable_documentation}")

    def run_single_test(self,
                       question: str,
                       with_documentation: bool = True) -> Dict[str, Any]:
        """Run a single test question.

        Args:
            question: Natural language question
            with_documentation: Whether to include documentation context

        Returns:
            Dict with test results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {question}")
        logger.info(f"Mode: {'WITH' if with_documentation else 'WITHOUT'} documentation")
        logger.info(f"{'='*60}")

        try:
            # Step 1: Analyze question
            analysis = self.analyzer.analyze_question(question)
            logger.info(f"Analysis - Domain: {analysis.get('domain')}, Intent: {analysis.get('intent')}")

            # Step 2: Retrieve similar examples
            retrieval_result = self.retriever.retrieve(question, analysis)
            logger.info(f"Retrieved {len(retrieval_result.get('similar_qa', []))} Q&A examples, "
                       f"{len(retrieval_result.get('cpgql_examples', []))} CPGQL examples")

            # Step 3: Get enrichment hints
            hints = self.enrichment.enrich(question, analysis)
            logger.info(f"Enrichment - Found {len(hints.get('tags', []))} relevant tags")

            # Step 4: Build context for generator
            context = {
                'similar_qa': retrieval_result.get('similar_qa', []),
                'cpgql_examples': retrieval_result.get('cpgql_examples', []),
                'analysis': analysis,
                'enrichment_hints': hints
            }

            # Step 5: Generate CPGQL query with appropriate generator
            generator = self.generator_with_docs if with_documentation else self.generator_without_docs
            cpgql_query, is_valid, error = generator.generate(question, context)

            logger.info(f"Generated query: {cpgql_query[:100]}...")
            logger.info(f"Query valid: {is_valid}")

            # Get prompt length for comparison
            prompt_context = ""
            if with_documentation:
                prompt_context = generator.enrichment_builder.build_full_enrichment_prompt(
                    hints=hints,
                    question=question,
                    analysis=analysis,
                    include_documentation=True
                )
            else:
                prompt_context = generator.enrichment_builder.build_enrichment_context(
                    hints=hints,
                    question=question,
                    analysis=analysis
                )

            # Step 6: Execute query
            if not self.joern_client.is_connected:
                self.joern_client.connect()

            exec_result = self.joern_client.execute_query(cpgql_query)

            return {
                'question': question,
                'with_documentation': with_documentation,
                'success': True,
                'analysis': analysis,
                'enrichment_tags_count': len(hints.get('tags', [])),
                'prompt_length': len(prompt_context),
                'query_length': len(cpgql_query),
                'query': cpgql_query,
                'query_valid': is_valid,
                'execution_success': exec_result.get('success', False),
                'result_size': len(str(exec_result.get('result', ''))),
                'error': error if not is_valid else exec_result.get('error'),
                'prompt_context': prompt_context[:500] + '...' if len(prompt_context) > 500 else prompt_context
            }

        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            return {
                'question': question,
                'with_documentation': with_documentation,
                'success': False,
                'error': str(e)
            }

    def run_validation_suite(self, output_file: str = "phase1_validation_results.json") -> Dict[str, Any]:
        """Run complete validation test suite.

        Args:
            output_file: Output file for results

        Returns:
            Dict with validation results
        """
        logger.info("\n" + "="*80)
        logger.info("PHASE 1 VALIDATION TEST SUITE")
        logger.info("="*80)
        logger.info(f"Total questions: {len(TEST_QUESTIONS)}")
        logger.info(f"Running each question WITH and WITHOUT documentation")
        logger.info(f"Total tests: {len(TEST_QUESTIONS) * 2}")

        results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_questions': len(TEST_QUESTIONS),
                'phase': 'Phase 1: Comments & Documentation Integration',
                'target_improvement': '10% → 35%'
            },
            'baseline': [],  # Without documentation
            'phase1': [],    # With documentation
            'statistics': {}
        }

        # Run tests
        for i, test_q in enumerate(TEST_QUESTIONS, 1):
            question = test_q['question']
            category = test_q['category']
            difficulty = test_q['difficulty']

            logger.info(f"\n{'='*80}")
            logger.info(f"Question {i}/{len(TEST_QUESTIONS)}: {category} [{difficulty}]")
            logger.info(f"{'='*80}")

            # Test WITHOUT documentation (baseline)
            baseline_result = self.run_single_test(question, with_documentation=False)
            baseline_result.update({
                'category': category,
                'difficulty': difficulty,
                'test_number': i
            })
            results['baseline'].append(baseline_result)

            # Test WITH documentation (Phase 1)
            phase1_result = self.run_single_test(question, with_documentation=True)
            phase1_result.update({
                'category': category,
                'difficulty': difficulty,
                'test_number': i
            })
            results['phase1'].append(phase1_result)

            # Log progress
            logger.info(f"\nProgress: {i}/{len(TEST_QUESTIONS)} questions completed")

        # Calculate statistics
        results['statistics'] = self._calculate_statistics(results)

        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        logger.info(f"\n{'='*80}")
        logger.info(f"Results saved to: {output_file}")
        logger.info(f"{'='*80}")

        return results

    def _calculate_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate validation statistics.

        Args:
            results: Validation results

        Returns:
            Statistics dict
        """
        baseline = results['baseline']
        phase1 = results['phase1']

        stats = {
            'baseline': {
                'total_tests': len(baseline),
                'successful_tests': sum(1 for r in baseline if r['success']),
                'successful_executions': sum(1 for r in baseline if r.get('execution_success')),
                'avg_prompt_length': sum(r.get('prompt_length', 0) for r in baseline if r['success']) / len([r for r in baseline if r['success']]) if baseline else 0,
                'avg_query_length': sum(r.get('query_length', 0) for r in baseline if r['success']) / len([r for r in baseline if r['success']]) if baseline else 0,
                'avg_result_size': sum(r.get('result_size', 0) for r in baseline if r.get('execution_success')) / len([r for r in baseline if r.get('execution_success')]) if baseline else 0
            },
            'phase1': {
                'total_tests': len(phase1),
                'successful_tests': sum(1 for r in phase1 if r['success']),
                'successful_executions': sum(1 for r in phase1 if r.get('execution_success')),
                'avg_prompt_length': sum(r.get('prompt_length', 0) for r in phase1 if r['success']) / len([r for r in phase1 if r['success']]) if phase1 else 0,
                'avg_query_length': sum(r.get('query_length', 0) for r in phase1 if r['success']) / len([r for r in phase1 if r['success']]) if phase1 else 0,
                'avg_result_size': sum(r.get('result_size', 0) for r in phase1 if r.get('execution_success')) / len([r for r in phase1 if r.get('execution_success')]) if phase1 else 0
            }
        }

        # Calculate improvements
        stats['improvements'] = {
            'prompt_length_increase_pct': ((stats['phase1']['avg_prompt_length'] - stats['baseline']['avg_prompt_length']) / stats['baseline']['avg_prompt_length'] * 100) if stats['baseline']['avg_prompt_length'] > 0 else 0,
            'query_length_increase_pct': ((stats['phase1']['avg_query_length'] - stats['baseline']['avg_query_length']) / stats['baseline']['avg_query_length'] * 100) if stats['baseline']['avg_query_length'] > 0 else 0,
            'execution_success_improvement': stats['phase1']['successful_executions'] - stats['baseline']['successful_executions']
        }

        return stats

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print validation summary.

        Args:
            results: Validation results
        """
        stats = results['statistics']

        print("\n" + "="*80)
        print("PHASE 1 VALIDATION SUMMARY")
        print("="*80)

        print("\nBASELINE (Without Documentation):")
        print(f"  Tests run: {stats['baseline']['total_tests']}")
        print(f"  Successful tests: {stats['baseline']['successful_tests']}")
        print(f"  Successful executions: {stats['baseline']['successful_executions']}")
        print(f"  Avg prompt length: {stats['baseline']['avg_prompt_length']:.0f} chars")
        print(f"  Avg query length: {stats['baseline']['avg_query_length']:.0f} chars")
        print(f"  Avg result size: {stats['baseline']['avg_result_size']:.0f} chars")

        print("\nPHASE 1 (With Documentation):")
        print(f"  Tests run: {stats['phase1']['total_tests']}")
        print(f"  Successful tests: {stats['phase1']['successful_tests']}")
        print(f"  Successful executions: {stats['phase1']['successful_executions']}")
        print(f"  Avg prompt length: {stats['phase1']['avg_prompt_length']:.0f} chars")
        print(f"  Avg query length: {stats['phase1']['avg_query_length']:.0f} chars")
        print(f"  Avg result size: {stats['phase1']['avg_result_size']:.0f} chars")

        print("\nIMPROVEMENTS:")
        print(f"  Prompt length increase: {stats['improvements']['prompt_length_increase_pct']:.1f}%")
        print(f"  Query length change: {stats['improvements']['query_length_increase_pct']:.1f}%")
        print(f"  Execution success improvement: {stats['improvements']['execution_success_improvement']} additional successful executions")

        print("\n" + "="*80)
        print("NOTE: Manual quality assessment required for answer completeness,")
        print("      technical accuracy, explanation depth, and code context relevance.")
        print("="*80 + "\n")


def main():
    """Main entry point for Phase 1 validation."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 1 validation test suite')
    parser.add_argument('--joern-host', default='localhost:8080',
                       help='Joern server host:port')
    parser.add_argument('--output', default='phase1_validation_results.json',
                       help='Output file for results')
    parser.add_argument('--question-limit', type=int,
                       help='Limit number of test questions')

    args = parser.parse_args()

    # Limit questions if requested
    global TEST_QUESTIONS
    if args.question_limit:
        TEST_QUESTIONS = TEST_QUESTIONS[:args.question_limit]
        logger.info(f"Limited to first {args.question_limit} questions")

    # Initialize validator
    logger.info("Initializing Phase1Validator...")
    validator = Phase1Validator(joern_host=args.joern_host)

    # Run validation suite
    results = validator.run_validation_suite(output_file=args.output)

    # Print summary
    validator.print_summary(results)

    print(f"\nDetailed results saved to: {args.output}")
    print("\nNext steps:")
    print("1. Review generated queries for quality and correctness")
    print("2. Manually assess answer quality (completeness, accuracy, depth)")
    print("3. Compare baseline vs Phase 1 answers")
    print("4. Calculate quality improvement percentage")
    print("5. Document findings in PHASE1_COMPLETION_SUMMARY.md")


if __name__ == '__main__':
    main()
