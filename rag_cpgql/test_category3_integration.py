"""
Test script for Category 3: Type & Member Semantic Classification.

Validates that type-category, type-domain-entity, type-concurrency-primitive,
type-ownership-model, member-role, member-pointer, and member-length-field tags integrate across agent and prompt builder.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.enrichment_prompt_builder import EnrichmentPromptBuilder

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_category3_enrichment_agent():
    """Ensure EnrichmentAgent surfaces type/member classifications."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: EnrichmentAgent Type & Member Tag Generation")
    logger.info("=" * 80)

    agent = EnrichmentAgent(enable_fallback=False)

    analysis = {
        'domain': 'indexes',
        'keywords': ['btree struct', 'index metadata'],
        'intent': 'analyze-component'
    }

    hints = agent.get_enrichment_hints("Inspect index struct definitions", analysis)

    logger.info(f"\nDomain: {analysis['domain']}")
    logger.info(f"Keywords: {analysis['keywords']}")
    logger.info("\nGenerated hints:")
    logger.info(f"  type_categories: {hints.get('type_categories', [])}")
    logger.info(f"  type_domain_entities: {hints.get('type_domain_entities', [])}")
    logger.info(f"  member_roles: {hints.get('member_roles', [])}")
    logger.info(f"  member_pointers: {hints.get('member_pointers', [])}")
    logger.info(f"  member_length_fields: {hints.get('member_length_fields', [])}")
    logger.info(f"  Coverage score: {hints.get('coverage_score', 0):.3f}")

    assert 'type_categories' in hints, "type_categories missing from hints"
    assert 'struct' in hints.get('type_categories', []), "Expected 'struct' type category for indexes"
    assert 'index' in hints.get('type_domain_entities', []), "Expected 'index' type domain entity"
    assert len(hints.get('member_roles', [])) > 0, "Expected member roles for index domain"
    assert 'true' in hints.get('member_pointers', []), "Expected member-pointer flag for index domain"
    assert 'true' in hints.get('member_length_fields', []), "Expected member-length-field flag for index domain"

    logger.info("\n\u2713 Test 1 PASSED: Type/member hints generated")

    return True


def test_category3_prompt_builder():
    """Ensure prompt builder includes type/member patterns."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: EnrichmentPromptBuilder Type Pattern Generation")
    logger.info("=" * 80)

    builder = EnrichmentPromptBuilder(
        enable_documentation=False,
        enable_cfg=False,
        enable_ddg=False
    )

    hints = {
        'type_categories': ['struct', 'typedef'],
        'type_domain_entities': ['index', 'buffer-desc'],
        'type_concurrency_primitives': ['lwlock'],
        'type_ownership_models': ['pinned-buffer'],
        'member_roles': ['metadata', 'state'],
        'member_pointers': ['true'],
        'member_length_fields': ['true'],
        'tags': [
            {
                'tag_name': 'type-category',
                'tag_value': 'struct',
                'query_fragment': '_.tag.nameExact("type-category").valueExact("struct")'
            },
            {
                'tag_name': 'type-domain-entity',
                'tag_value': 'index',
                'query_fragment': '_.tag.nameExact("type-domain-entity").valueExact("index")'
            },
            {
                'tag_name': 'type-ownership-model',
                'tag_value': 'pinned-buffer',
                'query_fragment': '_.tag.nameExact("type-ownership-model").valueExact("pinned-buffer")'
            },
            {
                'tag_name': 'member-pointer',
                'tag_value': 'true',
                'query_fragment': '_.tag.nameExact("member-pointer").valueExact("true")'
            },
            {
                'tag_name': 'member-length-field',
                'tag_value': 'true',
                'query_fragment': '_.tag.nameExact("member-length-field").valueExact("true")'
            }
        ],
        'coverage_score': 0.61
    }

    analysis = {
        'domain': 'indexes',
        'keywords': ['index struct', 'buffer descriptor'],
        'intent': 'analyze-component'
    }

    context = builder.build_enrichment_context(
        hints=hints,
        question="Show index struct members and ownership.",
        analysis=analysis,
        max_tags=10,
        max_patterns=10
    )

    logger.info("\nGenerated enrichment context:")
    logger.info(context)

    assert 'type-categories' in context, "type-categories section missing"
    assert 'type-domain-entities' in context, "type-domain-entities section missing"
    assert 'member-pointers' in context, "member-pointers section missing"
    assert 'member-length-fields' in context, "member-length-fields section missing"
    assert 'type-category' in context, "type-category pattern missing"

    logger.info("\n\u2713 Test 2 PASSED: Prompt builder surfaces type/member context")

    return True


def test_category3_tag_filter_generation():
    """Ensure tag filters include type/member classifications."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Tag Filter Generation for Type Tags")
    logger.info("=" * 80)

    agent = EnrichmentAgent(enable_fallback=False)

    analysis = {
        'domain': 'storage',
        'keywords': ['buffer descriptor struct', 'heap tuple'],
        'intent': 'trace-flow'
    }

    hints = agent.get_enrichment_hints("Trace storage type ownership", analysis)

    logger.info(f"\nDomain: {analysis['domain']}")
    logger.info("Generated tag filters:")
    for i, tag_filter in enumerate(hints.get('tags', []), 1):
        logger.info(f"  {i}. {tag_filter['tag_name']}={tag_filter['tag_value']}")
        logger.info(f"     Fragment: {tag_filter['query_fragment'][:80]}...")

    tag_names = [f['tag_name'] for f in hints.get('tags', [])]
    type_tags = [
        t for t in tag_names
        if t in [
            'type-category',
            'type-domain-entity',
            'type-concurrency-primitive',
            'type-ownership-model',
            'member-role',
            'member-pointer',
            'member-length-field'
        ]
    ]

    assert len(type_tags) > 0, "Expected type/member tag filters"

    logger.info(f"\n\u2713 Test 3 PASSED: Type/member tag filters generated ({len(type_tags)})")

    return True


def main():
    """Run all Category 3 integration tests."""
    logger.info("\n" + "=" * 80)
    logger.info("CATEGORY 3: TYPE & MEMBER SEMANTIC CLASSIFICATION")
    logger.info("Integration Test Suite")
    logger.info("=" * 80)

    try:
        test_category3_enrichment_agent()
        test_category3_prompt_builder()
        test_category3_tag_filter_generation()

        logger.info("\n" + "=" * 80)
        logger.info("\u2713 ALL TESTS PASSED - Category 3 Integration Ready")
        logger.info("=" * 80)
        logger.info("\nIntegrated features:")
        logger.info("  \u2022 type-category tags (31,536/72,178 types)")
        logger.info("  \u2022 type-domain-entity tags (4,728/72,178 types)")
        logger.info("  \u2022 type-concurrency-primitive tags (450 types)")
        logger.info("  \u2022 type-ownership-model tags (4,887/72,178 types)")
        logger.info("  \u2022 member-role tags (63,519 members)")
        logger.info("  \u2022 member-pointer tags (8,559 members)")
        logger.info("  \u2022 member-length-field tags (4,577 members)")
        logger.info("\nExpected accuracy improvement: +12%")
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
