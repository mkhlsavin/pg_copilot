"""
Simple Phase 1 Validation - Test documentation retrieval impact

This simplified test focuses on measuring whether documentation retrieval
provides relevant context for PostgreSQL questions.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from src.agents.analyzer_agent import AnalyzerAgent
from src.retrieval.documentation_retriever import DocumentationRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Test questions
TEST_QUESTIONS = [
    {"question": "How does PostgreSQL implement MVCC for transaction isolation?", "category": "transaction"},
    {"question": "How does PostgreSQL's BRIN index work for range queries?", "category": "indexing"},
    {"question": "How does PostgreSQL manage the shared buffer pool?", "category": "storage"},
    {"question": "How does PostgreSQL check access permissions using ACL?", "category": "catalog"},
    {"question": "How does PostgreSQL implement two-phase commit for distributed transactions?", "category": "transaction"},
    {"question": "How does PostgreSQL implement GIN index for full-text search?", "category": "indexing"},
    {"question": "How does PostgreSQL implement write-ahead logging (WAL)?", "category": "storage"},
    {"question": "How does PostgreSQL implement row-level security policies?", "category": "catalog"},
    {"question": "How does PostgreSQL determine tuple visibility in a multi-version snapshot?", "category": "transaction"},
    {"question": "How does PostgreSQL maintain index consistency during concurrent updates?", "category": "indexing"},
    {"question": "How does PostgreSQL handle page checksums for data corruption detection?", "category": "storage"},
    {"question": "How does PostgreSQL manage system catalog updates during DDL?", "category": "catalog"},
    {"question": "How does PostgreSQL handle transaction rollback and cleanup?", "category": "transaction"},
    {"question": "How does PostgreSQL perform index vacuum and cleanup?", "category": "indexing"},
    {"question": "How does PostgreSQL implement heap tuple storage and organization?", "category": "storage"},
    {"question": "How does PostgreSQL handle large object access control?", "category": "catalog"},
    {"question": "How does PostgreSQL prevent phantom reads in repeatable read isolation?", "category": "transaction"},
    {"question": "How does PostgreSQL choose between sequential and index scan?", "category": "indexing"},
    {"question": "How does PostgreSQL perform vacuum to reclaim dead tuple space?", "category": "storage"},
    {"question": "How does PostgreSQL prevent operations inside transaction blocks?", "category": "catalog"}
]


def test_documentation_retrieval():
    """Test documentation retrieval for all questions."""

    logger.info("="*80)
    logger.info("PHASE 1 SIMPLE VALIDATION: Documentation Retrieval Test")
    logger.info("="*80)

    # Initialize components
    logger.info("\nInitializing components...")
    analyzer = AnalyzerAgent()
    doc_retriever = DocumentationRetriever()

    # Get stats
    stats = doc_retriever.get_stats()
    logger.info(f"Documentation collection: {stats['total_documents']} documents indexed")

    # Test all questions
    results = []

    for i, test_q in enumerate(TEST_QUESTIONS, 1):
        question = test_q['question']
        category = test_q['category']

        logger.info(f"\n{'='*80}")
        logger.info(f"Question {i}/{len(TEST_QUESTIONS)}: {category}")
        logger.info(f"{'='*80}")
        logger.info(f"Q: {question}")

        # Analyze question
        analysis = analyzer.analyze(question)
        logger.info(f"Analysis - Domain: {analysis.get('domain')}, Keywords: {analysis.get('keywords', [])[:3]}")

        # Retrieve documentation
        doc_result = doc_retriever.retrieve_relevant_documentation(
            question=question,
            analysis=analysis,
            top_k=5
        )

        # Log results
        doc_count = len(doc_result['documentation'])
        avg_relevance = doc_result['stats']['avg_relevance']
        top_relevance = doc_result['stats']['top_relevance']

        logger.info(f"Retrieved {doc_count} docs, avg_relevance={avg_relevance:.3f}, top_relevance={top_relevance:.3f}")

        if doc_result['documentation']:
            logger.info(f"\nTop documentation:")
            for j, doc in enumerate(doc_result['documentation'][:3], 1):
                logger.info(f"  {j}. {doc['method_name']} (relevance: {doc['relevance_score']:.3f})")
                logger.info(f"     {doc['file_path']}:{doc['line_number']}")
                logger.info(f"     Comment: {doc['comment'][:100]}...")

        # Save result
        results.append({
            'question': question,
            'category': category,
            'test_number': i,
            'analysis': {
                'domain': analysis.get('domain'),
                'intent': analysis.get('intent'),
                'keywords': analysis.get('keywords', [])
            },
            'documentation_count': doc_count,
            'avg_relevance': avg_relevance,
            'top_relevance': top_relevance,
            'top_methods': [
                {
                    'method_name': doc['method_name'],
                    'file_path': doc['file_path'],
                    'relevance': doc['relevance_score'],
                    'comment_preview': doc['comment'][:200]
                }
                for doc in doc_result['documentation'][:3]
            ],
            'has_relevant_docs': avg_relevance >= 0.25  # Threshold from retriever
        })

    # Calculate statistics
    total_tests = len(results)
    tests_with_relevant_docs = sum(1 for r in results if r['has_relevant_docs'])
    avg_doc_count = sum(r['documentation_count'] for r in results) / total_tests
    avg_relevance_overall = sum(r['avg_relevance'] for r in results) / total_tests
    avg_top_relevance = sum(r['top_relevance'] for r in results) / total_tests

    # Category breakdown
    category_stats = {}
    for category in set(r['category'] for r in results):
        cat_results = [r for r in results if r['category'] == category]
        category_stats[category] = {
            'total': len(cat_results),
            'with_relevant_docs': sum(1 for r in cat_results if r['has_relevant_docs']),
            'avg_relevance': sum(r['avg_relevance'] for r in cat_results) / len(cat_results),
            'avg_doc_count': sum(r['documentation_count'] for r in cat_results) / len(cat_results)
        }

    # Summary
    summary = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 1: Documentation Retrieval Test',
            'total_questions': total_tests,
            'document_collection_size': stats['total_documents']
        },
        'results': results,
        'statistics': {
            'total_tests': total_tests,
            'tests_with_relevant_docs': tests_with_relevant_docs,
            'success_rate': tests_with_relevant_docs / total_tests,
            'avg_documents_per_question': avg_doc_count,
            'avg_relevance_overall': avg_relevance_overall,
            'avg_top_relevance': avg_top_relevance,
            'category_breakdown': category_stats
        }
    }

    # Save results
    output_file = 'phase1_simple_validation_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print("\n" + "="*80)
    print("PHASE 1 DOCUMENTATION RETRIEVAL SUMMARY")
    print("="*80)
    print(f"\nTotal questions tested: {total_tests}")
    print(f"Questions with relevant documentation: {tests_with_relevant_docs} ({tests_with_relevant_docs/total_tests*100:.1f}%)")
    print(f"Average documents per question: {avg_doc_count:.1f}")
    print(f"Average relevance: {avg_relevance_overall:.3f}")
    print(f"Average top relevance: {avg_top_relevance:.3f}")

    print(f"\nCategory Breakdown:")
    for category, cat_stats in category_stats.items():
        print(f"  {category}:")
        print(f"    Tests: {cat_stats['total']}")
        print(f"    With docs: {cat_stats['with_relevant_docs']} ({cat_stats['with_relevant_docs']/cat_stats['total']*100:.1f}%)")
        print(f"    Avg relevance: {cat_stats['avg_relevance']:.3f}")
        print(f"    Avg doc count: {cat_stats['avg_doc_count']:.1f}")

    print(f"\nResults saved to: {output_file}")
    print("="*80)

    # Quality assessment
    print("\n" + "="*80)
    print("QUALITY ASSESSMENT")
    print("="*80)

    if avg_relevance_overall >= 0.30:
        print("✅ EXCELLENT: Average relevance >= 0.30 indicates high-quality documentation retrieval")
    elif avg_relevance_overall >= 0.25:
        print("✅ GOOD: Average relevance >= 0.25 indicates good documentation retrieval")
    elif avg_relevance_overall >= 0.20:
        print("⚠️  MODERATE: Average relevance >= 0.20 indicates moderate documentation quality")
    else:
        print("❌ POOR: Average relevance < 0.20 indicates low documentation relevance")

    if tests_with_relevant_docs / total_tests >= 0.80:
        print(f"✅ COVERAGE: {tests_with_relevant_docs/total_tests*100:.1f}% of questions have relevant documentation")
    else:
        print(f"⚠️  COVERAGE: Only {tests_with_relevant_docs/total_tests*100:.1f}% of questions have relevant documentation")

    print("\nNext Steps:")
    print("1. Review top retrieved methods for each question")
    print("2. Assess whether documentation explains 'how' the functionality works")
    print("3. Compare this baseline with query generation quality")
    print("4. Document findings in PHASE1_COMPLETION_SUMMARY.md")
    print("="*80)

    return summary


if __name__ == '__main__':
    test_documentation_retrieval()
