"""Enrichment Agent - Maps questions to CPG enrichment tags."""
import logging
from typing import Dict, List

from .._tag_mappings import build_tag_mappings
from .keyword_matchers import enhance_with_keywords
from .fallback import general_domain_fallback
from .tag_filters import generate_tag_filters
from .coverage import calculate_coverage
from .prompt_formatter import format_for_prompt, get_example_queries

logger = logging.getLogger(__name__)

# Phase 4: Import fallback strategies
try:
    from src.agents.fallback_strategies import get_fallback_selector
    FALLBACK_AVAILABLE = True
except ImportError:
    logger.warning("Fallback strategies not available, Phase 4 features disabled")
    FALLBACK_AVAILABLE = False


def _create_empty_hints() -> Dict:
    """Create an empty hints dictionary with all categories."""
    return {
        # Existing categories
        'function_purposes': [],
        'data_structures': [],
        'algorithms': [],
        'domain_concepts': [],
        'features': [],
        # Category 1: Parameter & Return Semantic Integration
        'param_roles': [],
        'return_kinds': [],
        'return_outcomes': [],
        'validation_required': [],
        # Category 2: Variable & Identifier Semantic Enhancement
        'variable_roles': [],
        'data_kinds': [],
        'security_sensitivities': [],
        'lifetimes': [],
        'mutabilities': [],
        'is_locks': [],
        'is_pointer_to_structs': [],
        # Category 3: Type & Member Semantic Classification
        'type_categories': [],
        'type_domain_entities': [],
        'type_concurrency_primitives': [],
        'type_ownership_models': [],
        'member_roles': [],
        'member_pointers': [],
        'member_length_fields': [],
        # Category 4: Literal & Constant Semantic Understanding
        'literal_kinds': [],
        'literal_domains': [],
        'literal_severities': [],
        'is_null_constants': [],
        'is_bitmasks': [],
        'literal_constants': [],
        'is_lock_constants': [],
        # Category 5: Control Flow & Jump Semantics
        'jump_kinds': [],
        'jump_domains': [],
        'jump_scopes': [],
        'modifier_concurrencies': [],
        'modifier_attributes': [],
        # Category 6: Namespace & Reference
        'namespace_layers': [],
        'namespace_domains': [],
        'method_ref_kinds': [],
        'method_ref_usages': [],
        # Category 7: Data Flow & Edge Semantic Enrichment
        'data_flow_kinds': [],
        'child_roles': [],
        'call_actions': [],
        'call_side_effects': [],
        'call_receiver_roles': [],
        'argument_param_names': [],
        'branch_kinds': [],
        'control_reasons': [],
    }


class EnrichmentAgent:
    """
    Enrichment Agent for CPG tag mapping.

    Maps question analysis to relevant enrichment tags from the
    12-layer CPG enrichment system.
    """

    def __init__(self, enable_fallback: bool = True):
        """
        Initialize Enrichment Agent with tag mappings.

        Args:
            enable_fallback: Enable Phase 4 fallback strategies for low coverage
        """
        # Load enrichment tag mappings
        self.tag_mappings = build_tag_mappings()

        # Phase 4: Fallback strategy selector
        self.enable_fallback = enable_fallback and FALLBACK_AVAILABLE
        self.fallback_selector = get_fallback_selector() if self.enable_fallback else None

    def get_enrichment_hints(
        self,
        question: str,
        analysis: Dict
    ) -> Dict:
        """
        Get enrichment tag hints based on question analysis.

        Args:
            question: Original question
            analysis: Analysis from AnalyzerAgent

        Returns:
            Dictionary with enrichment hints (ONLY valid CPG tag categories)
        """
        domain = analysis.get('domain', 'general')
        keywords = analysis.get('keywords', [])
        intent = analysis.get('intent', 'explain-concept')

        hints = _create_empty_hints()

        # Map domain to enrichment tags (ONLY valid CPG tag categories)
        if domain != 'general':
            self._apply_domain_mappings(hints, domain)

        # Enhance with keyword-based matching
        hints = enhance_with_keywords(hints, keywords)

        # Fallback for general domain
        if domain == 'general' and not any(hints.values()):
            hints = general_domain_fallback(hints, keywords)

        # Generate CPGQL tag filter suggestions
        hints['tags'] = generate_tag_filters(hints)

        # Calculate coverage score
        hints['coverage_score'] = calculate_coverage(hints)

        logger.info(f"Generated enrichment hints for domain='{domain}': "
                   f"{len(hints['tags'])} tag filters, "
                   f"coverage={hints['coverage_score']:.2f}")

        # Phase 4: Apply fallback strategies if coverage is low
        if self.enable_fallback and self.fallback_selector:
            if hints['coverage_score'] < 0.4:
                logger.info(f"Coverage {hints['coverage_score']:.2f} is low, applying fallback strategies")
                hints = self.fallback_selector.apply_fallback(hints, question, analysis)

        return hints

    def _apply_domain_mappings(self, hints: Dict, domain: str) -> None:
        """Apply domain-specific mappings to hints."""
        # Map of hint key to tag mapping key
        mappings = [
            ('function_purposes', 'function_purpose'),
            ('data_structures', 'data_structure'),
            ('algorithms', 'algorithm'),
            ('domain_concepts', 'domain_concept'),
            ('features', 'feature'),
            # Category 1: Parameter & Return
            ('param_roles', 'param_role'),
            ('return_kinds', 'return_kind'),
            ('return_outcomes', 'return_outcome'),
            ('validation_required', 'validation_required'),
            # Category 2: Variable & Identifier
            ('variable_roles', 'variable_role'),
            ('data_kinds', 'data_kind'),
            ('security_sensitivities', 'security_sensitivity'),
            ('lifetimes', 'lifetime'),
            ('mutabilities', 'mutability'),
            ('is_locks', 'is_lock'),
            ('is_pointer_to_structs', 'is_pointer_to_struct'),
            # Category 3: Type & Member
            ('type_categories', 'type_category'),
            ('type_domain_entities', 'type_domain_entity'),
            ('type_concurrency_primitives', 'type_concurrency_primitive'),
            ('type_ownership_models', 'type_ownership_model'),
            ('member_roles', 'member_role'),
            ('member_pointers', 'member_pointer'),
            ('member_length_fields', 'member_length_field'),
            # Category 4: Literal & Constant
            ('literal_kinds', 'literal_kind'),
            ('literal_domains', 'literal_domain'),
            ('literal_severities', 'literal_severity'),
            ('is_null_constants', 'is_null_constant'),
            ('is_bitmasks', 'is_bitmask'),
            ('literal_constants', 'literal_constant'),
            ('is_lock_constants', 'is_lock_constant'),
            # Category 5: Control Flow & Jump
            ('jump_kinds', 'jump_kind'),
            ('jump_domains', 'jump_domain'),
            ('jump_scopes', 'jump_scope'),
            ('modifier_concurrencies', 'modifier_concurrency'),
            ('modifier_attributes', 'modifier_attribute'),
            # Category 6: Namespace & Reference
            ('namespace_layers', 'namespace_layer'),
            ('namespace_domains', 'namespace_domain'),
            ('method_ref_kinds', 'method_ref_kind'),
            ('method_ref_usages', 'method_ref_usage'),
            # Category 7: Data Flow & Edge
            ('data_flow_kinds', 'data_flow_kind'),
            ('child_roles', 'child_role'),
            ('call_actions', 'call_action'),
            ('call_side_effects', 'call_side_effect'),
            ('call_receiver_roles', 'call_receiver_role'),
            ('argument_param_names', 'argument_param_name'),
            ('branch_kinds', 'branch_kind'),
            ('control_reasons', 'control_reason'),
        ]

        for hint_key, mapping_key in mappings:
            if domain in self.tag_mappings.get(mapping_key, {}):
                hints[hint_key] = self.tag_mappings[mapping_key][domain]

    def format_for_prompt(self, hints: Dict) -> str:
        """
        Format enrichment hints for inclusion in LLM prompt.

        Args:
            hints: Dictionary of enrichment hints

        Returns:
            Formatted string for prompt context
        """
        return format_for_prompt(hints)

    def get_example_queries(self, hints: Dict, limit: int = 5) -> List[str]:
        """
        Generate example CPGQL queries using enrichment tags.

        Args:
            hints: Enrichment hints
            limit: Maximum number of examples

        Returns:
            List of example CPGQL queries
        """
        return get_example_queries(hints, limit)


__all__ = ['EnrichmentAgent']
