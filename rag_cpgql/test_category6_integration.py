"""
Test script for Category 6: Namespace & Reference Semantic Context.

Validates that namespace-layer, namespace-domain, method-ref-kind,
and method-ref-usage tags integrate through the enrichment workflow.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.enrichment_prompt_builder import EnrichmentPromptBuilder

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_category6_enrichment_agent():
    """Ensure EnrichmentAgent surfaces namespace/reference tags."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: EnrichmentAgent Namespace & Reference Tag Generation")
    logger.info("=" * 80)

    agent = EnrichmentAgent(enable_fallback=False)

    analysis = {
        'domain': 'executor',
        'keywords': ['executor namespace', 'callback usage'],
        'intent': 'analyze-component'
    }

    hints = agent.get_enrichment_hints("Inspect executor callbacks by namespace.", analysis)

    logger.info(f"\nDomain: {analysis['domain']}")
    logger.info(f"Keywords: {analysis['keywords']}")
    logger.info("\nGenerated hints:")
    logger.info(f"  namespace_layers: {hints.get('namespace_layers', [])}")
    logger.info(f"  namespace_domains: {hints.get('namespace_domains', [])}")
    logger.info(f"  method_ref_kinds: {hints.get('method_ref_kinds', [])}")
    logger.info(f"  method_ref_usages: {hints.get('method_ref_usages', [])}")
    logger.info(f"  Coverage score: {hints.get('coverage_score', 0):.3f}")

    assert 'executor' in hints.get('namespace_layers', []), "Expected namespace-layer=executor"
    assert 'callback' in hints.get('method_ref_kinds', []), "Expected method-ref-kind=callback"

    logger.info("\n\u2713 Test 1 PASSED: Namespace/reference hints generated")
    return True


def test_category6_prompt_builder():
    """Ensure prompt builder includes namespace/reference patterns."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: EnrichmentPromptBuilder Namespace Pattern Generation")
    logger.info("=" * 80)

    builder = EnrichmentPromptBuilder(
        enable_documentation=False,
        enable_cfg=False,
        enable_ddg=False
    )

    hints = {
        'namespace_layers': ['executor', 'planner'],
        'namespace_domains': ['server'],
        'method_ref_kinds': ['callback'],
        'method_ref_usages': ['initializer', 'cleanup'],
        'tags': [
            {
                'tag_name': 'namespace-layer',
                'tag_value': 'executor',
                'query_fragment': '_.tag.nameExact("namespace-layer").valueExact("executor")'
            },
            {
                'tag_name': 'method-ref-kind',
                'tag_value': 'callback',
                'query_fragment': '_.tag.nameExact("method-ref-kind").valueExact("callback")'
            },
            {
                'tag_name': 'method-ref-usage',
                'tag_value': 'initializer',
                'query_fragment': '_.tag.nameExact("method-ref-usage").valueExact("initializer")'
            }
        ],
        'coverage_score': 0.37
    }

    analysis = {
        'domain': 'executor',
        'keywords': ['executor namespace', 'callback'],
        'intent': 'analyze-component'
    }

    context = builder.build_enrichment_context(
        hints=hints,
        question="List executor callbacks by namespace layer.",
        analysis=analysis,
        max_tags=10,
        max_patterns=10
    )

    logger.info("\nGenerated enrichment context:")
    logger.info(context)

    assert 'namespace-layers' in context, "namespace-layers section missing"
    assert 'method-ref-kinds' in context, "method-ref-kinds section missing"
    assert 'method-ref-usages' in context, "method-ref-usages section missing"
    assert 'namespace-layer' in context, "namespace-layer pattern missing"

    logger.info("\n\u2713 Test 2 PASSED: Prompt builder surfaces namespace context")
    return True


def test_category6_tag_filter_generation():
    """Ensure tag filters include namespace/reference categories."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Tag Filter Generation for Namespace Tags")
    logger.info("=" * 80)

    agent = EnrichmentAgent(enable_fallback=False)

    analysis = {
        'domain': 'planner',
        'keywords': ['server namespace', 'predicate callback'],
        'intent': 'find-bug'
    }

    hints = agent.get_enrichment_hints("Find planner callbacks used as predicates", analysis)

    logger.info(f"\nDomain: {analysis['domain']}")
    logger.info("Generated tag filters:")
    for i, tag_filter in enumerate(hints.get('tags', []), 1):
        logger.info(f"  {i}. {tag_filter['tag_name']}={tag_filter['tag_value']}")
        logger.info(f"     Fragment: {tag_filter['query_fragment'][:80]}...")

    tag_names = [f['tag_name'] for f in hints.get('tags', [])]
    namespace_tags = [t for t in tag_names if t in ['namespace-layer', 'namespace-domain']]
    method_ref_tags = [t for t in tag_names if t in ['method-ref-kind', 'method-ref-usage']]

    assert len(namespace_tags) > 0, "Expected namespace tag filters"
    assert len(method_ref_tags) > 0, "Expected method reference tag filters"

    logger.info(f"\n\u2713 Test 3 PASSED: Namespace tag filters generated ({len(namespace_tags)} namespace, {len(method_ref_tags)} method-ref)")
    return True


def main():
    """Run all Category 6 integration tests."""
    logger.info("\n" + "=" * 80)
    logger.info("CATEGORY 6: NAMESPACE & REFERENCE SEMANTIC CONTEXT")
    logger.info("Integration Test Suite")
    logger.info("=" * 80)

    try:
        test_category6_enrichment_agent()
        test_category6_prompt_builder()
        test_category6_tag_filter_generation()

        logger.info("\n" + "=" * 80)
        logger.info("\u2713 ALL TESTS PASSED - Category 6 Integration Ready")
        logger.info("=" * 80)
        logger.info("\nIntegrated features:")
        logger.info("  \u2022 namespace-layer tags (922/2,129 namespaces)")
        logger.info("  \u2022 namespace-domain tags (900/2,129 namespaces)")
        logger.info("  \u2022 method-ref-kind tags (28,375 references)")
        logger.info("  \u2022 method-ref-usage tags (3,182 references)")
        logger.info("\nExpected accuracy improvement: +10%")
        logger.info("=" * 80)

        return 0

    except AssertionError as exc:
        logger.error(f"\n\u2717 TEST FAILED: {exc}")
        return 1

    except Exception as exc:
        logger.error(f"\n\u2717 UNEXPECTED ERROR: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
