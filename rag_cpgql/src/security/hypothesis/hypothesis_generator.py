"""
Hypothesis Generator for Security Analysis.

Generates testable security hypotheses by combining:
- CWE vulnerability patterns
- CAPEC attack patterns
- Language-specific sinks/sources
- Codebase-specific context

The generator produces hypotheses in the form:
"If [source] flows to [sink] without [sanitizer], then [CWE] enables [attack]"
"""

import uuid
from datetime import datetime
from itertools import product
from typing import Dict, List, Optional, Set, Tuple

from .models import (
    SecurityHypothesis,
    HypothesisBatch,
    CWEEntry,
    CAPECPattern,
    LanguagePattern,
    ValidationStatus,
)
from .knowledge_base import SecurityKnowledgeBase, get_knowledge_base


class HypothesisGenerator:
    """Generates security hypotheses from knowledge base patterns.

    Uses multi-criteria hypothesis generation algorithm:
    1. ENUMERATION: Get CWEs, CAPECs, and patterns for language
    2. CARTESIAN PRODUCT: CWEs × AttackMethods × Sinks × Sources
    3. TEMPLATE INSTANTIATION: Create hypothesis statements
    4. FILTERING: Remove low-quality or duplicate hypotheses
    """

    # Hypothesis text templates by vulnerability category
    HYPOTHESIS_TEMPLATES = {
        "buffer_overflow": (
            "If untrusted data from {sources} flows to {sinks} without bounds checking "
            "via {sanitizers}, then {cwe} ({cwe_name}) enables {attack} attack, "
            "potentially allowing memory corruption or code execution."
        ),
        "format_string": (
            "If user-controlled input from {sources} is passed as format string to {sinks}, "
            "then {cwe} ({cwe_name}) enables {attack} attack, "
            "potentially allowing memory disclosure or arbitrary writes."
        ),
        "command_injection": (
            "If untrusted data from {sources} flows to command execution via {sinks} "
            "without proper escaping ({sanitizers}), then {cwe} ({cwe_name}) enables {attack} attack, "
            "allowing arbitrary command execution."
        ),
        "sql_injection": (
            "If user input from {sources} is incorporated into SQL queries via {sinks} "
            "without parameterization ({sanitizers}), then {cwe} ({cwe_name}) enables {attack} attack, "
            "allowing data extraction or manipulation."
        ),
        "code_injection": (
            "If untrusted data from {sources} flows to code generation via {sinks} "
            "without validation, then {cwe} ({cwe_name}) enables {attack} attack, "
            "allowing arbitrary code execution."
        ),
        "information_disclosure": (
            "If sensitive data is accessed via {sinks} without authorization checks ({sanitizers}), "
            "then {cwe} ({cwe_name}) enables {attack} attack, "
            "potentially exposing confidential information."
        ),
        "use_after_free": (
            "If memory freed by {sources} is subsequently accessed via {sinks} "
            "without proper null-checks, then {cwe} ({cwe_name}) enables {attack} attack, "
            "potentially allowing code execution."
        ),
        "integer_overflow": (
            "If arithmetic operations from {sources} lead to size calculations for {sinks} "
            "without overflow checks ({sanitizers}), then {cwe} ({cwe_name}) enables {attack} attack, "
            "potentially causing buffer overflows."
        ),
        "default": (
            "If data from {sources} flows to {sinks} without proper validation ({sanitizers}), "
            "then {cwe} ({cwe_name}) may be exploitable via {attack} attack pattern."
        ),
    }

    # Category mapping from CWE to template
    CWE_CATEGORY_MAP = {
        "CWE-120": "buffer_overflow",
        "CWE-119": "buffer_overflow",
        "CWE-787": "buffer_overflow",
        "CWE-125": "buffer_overflow",
        "CWE-134": "format_string",
        "CWE-78": "command_injection",
        "CWE-89": "sql_injection",
        "CWE-94": "code_injection",
        "CWE-95": "code_injection",
        "CWE-200": "information_disclosure",
        "CWE-209": "information_disclosure",
        "CWE-862": "information_disclosure",
        "CWE-416": "use_after_free",
        "CWE-415": "use_after_free",
        "CWE-190": "integer_overflow",
        "CWE-191": "integer_overflow",
    }

    def __init__(self, knowledge_base: Optional[SecurityKnowledgeBase] = None):
        """Initialize hypothesis generator.

        Args:
            knowledge_base: Security knowledge base instance.
                           Uses default singleton if not provided.
        """
        self.kb = knowledge_base or get_knowledge_base()

    def generate_hypotheses(
        self,
        language: str = "C",
        max_hypotheses: int = 100,
        categories: Optional[List[str]] = None,
        cwe_filter: Optional[List[str]] = None,
        min_risk_score: float = 0.0,
    ) -> List[SecurityHypothesis]:
        """Generate security hypotheses for a language.

        Args:
            language: Target programming language (default: "C")
            max_hypotheses: Maximum number of hypotheses to generate
            categories: Filter by vulnerability categories (e.g., ["buffer_overflow"])
            cwe_filter: Filter by specific CWE IDs
            min_risk_score: Minimum CWE risk score threshold

        Returns:
            List of SecurityHypothesis objects sorted by estimated priority
        """
        hypotheses: List[SecurityHypothesis] = []

        # Phase 1: ENUMERATION
        cwes = self._get_relevant_cwes(language, cwe_filter, min_risk_score)
        patterns = self.kb.get_patterns_by_language(language)

        if categories:
            patterns = [p for p in patterns if p.category in categories]

        # Phase 2: Generate hypotheses for each pattern
        for pattern in patterns:
            pattern_hypotheses = self._generate_for_pattern(pattern, cwes)
            hypotheses.extend(pattern_hypotheses)

        # Phase 3: Deduplicate and filter
        hypotheses = self._deduplicate(hypotheses)
        hypotheses = self._filter_quality(hypotheses)

        # Phase 4: Sort by estimated priority and limit
        hypotheses = sorted(
            hypotheses,
            key=lambda h: h.priority_score,
            reverse=True
        )[:max_hypotheses]

        return hypotheses

    def generate_for_cve(
        self,
        cve_id: str,
        language: str = "C",
    ) -> List[SecurityHypothesis]:
        """Generate hypotheses specifically targeting a known CVE.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2025-8714")
            language: Target programming language

        Returns:
            List of hypotheses that could detect the CVE pattern
        """
        from .postgresql import get_pg_pattern_for_cve

        cve_pattern = get_pg_pattern_for_cve(cve_id)
        if not cve_pattern:
            return []

        hypotheses = []

        for cwe_id in cve_pattern.cwes:
            cwe = self.kb.get_cwe(cwe_id)
            if not cwe:
                continue

            capecs = self.kb.get_capecs_for_cwe(cwe_id)
            attack_name = capecs[0].name if capecs else "exploitation"

            hypothesis = SecurityHypothesis(
                id=str(uuid.uuid4()),
                hypothesis_text=self._format_hypothesis_text(
                    category=self.CWE_CATEGORY_MAP.get(cwe_id, "default"),
                    sources=cve_pattern.sources[:3],
                    sinks=cve_pattern.sinks[:3],
                    sanitizers=cve_pattern.sanitizers[:3],
                    cwe=cwe_id,
                    cwe_name=cwe.name,
                    attack=attack_name,
                ),
                cwe_ids=[cwe_id],
                capec_ids=[c.id for c in capecs],
                language=language,
                category=self.CWE_CATEGORY_MAP.get(cwe_id, "vulnerability"),
                source_patterns=cve_pattern.sources,
                sink_patterns=cve_pattern.sinks,
                sanitizer_patterns=cve_pattern.sanitizers,
                # Pre-fill the query from CVE pattern
                sql_query=cve_pattern.detection_query,
                # Higher initial priority for CVE-targeted hypotheses
                priority_score=0.8,
                cwe_frequency_score=cwe.prevalence,
                tags=[cve_id, "cve-targeted"],
                notes=f"Generated for {cve_id}: {cve_pattern.description[:100]}...",
            )
            hypotheses.append(hypothesis)

        return hypotheses

    def create_batch(
        self,
        hypotheses: List[SecurityHypothesis],
        name: str,
        target_project: str,
        description: str = "",
    ) -> HypothesisBatch:
        """Create a batch of hypotheses for processing.

        Args:
            hypotheses: List of hypotheses to include
            name: Batch name
            target_project: Target project identifier
            description: Batch description

        Returns:
            HypothesisBatch object
        """
        return HypothesisBatch(
            id=str(uuid.uuid4()),
            name=name,
            description=description or f"Hypothesis batch for {target_project}",
            hypotheses=hypotheses,
            target_project=target_project,
        )

    def _get_relevant_cwes(
        self,
        language: str,
        cwe_filter: Optional[List[str]],
        min_risk_score: float,
    ) -> List[CWEEntry]:
        """Get relevant CWEs for hypothesis generation."""
        cwes = self.kb.get_cwes_by_language(language)

        if cwe_filter:
            cwes = [c for c in cwes if c.id in cwe_filter]

        if min_risk_score > 0:
            cwes = [c for c in cwes if c.risk_score >= min_risk_score]

        return cwes

    def _generate_for_pattern(
        self,
        pattern: LanguagePattern,
        cwes: List[CWEEntry],
    ) -> List[SecurityHypothesis]:
        """Generate hypotheses for a single language pattern."""
        hypotheses = []

        # Get CWEs relevant to this pattern
        pattern_cwes = [c for c in cwes if c.id in pattern.related_cwes]

        for cwe in pattern_cwes:
            # Get attack patterns for this CWE
            capecs = self.kb.get_capecs_for_cwe(cwe.id)

            # Generate hypothesis
            hypothesis = self._create_hypothesis(pattern, cwe, capecs)
            hypotheses.append(hypothesis)

        return hypotheses

    def _create_hypothesis(
        self,
        pattern: LanguagePattern,
        cwe: CWEEntry,
        capecs: List[CAPECPattern],
    ) -> SecurityHypothesis:
        """Create a single hypothesis from pattern and CWE."""
        attack_name = capecs[0].name if capecs else "exploitation"
        category = self.CWE_CATEGORY_MAP.get(cwe.id, "default")

        # Format hypothesis text
        hypothesis_text = self._format_hypothesis_text(
            category=category,
            sources=pattern.sources[:3],
            sinks=pattern.sinks[:3],
            sanitizers=pattern.sanitizers[:3] if pattern.sanitizers else ["validation"],
            cwe=cwe.id,
            cwe_name=cwe.name,
            attack=attack_name,
        )

        # Estimate initial priority based on CWE risk
        initial_priority = cwe.risk_score

        return SecurityHypothesis(
            id=str(uuid.uuid4()),
            hypothesis_text=hypothesis_text,
            cwe_ids=[cwe.id] + cwe.related_cwes[:2],
            capec_ids=[c.id for c in capecs],
            language=pattern.language,
            category=pattern.category,
            source_patterns=pattern.sources,
            sink_patterns=pattern.sinks,
            sanitizer_patterns=pattern.sanitizers,
            priority_score=initial_priority,
            cwe_frequency_score=cwe.prevalence,
            attack_similarity_score=capecs[0].likelihood if capecs else 0.5,
            tags=[cwe.severity.value, pattern.category],
        )

    def _format_hypothesis_text(
        self,
        category: str,
        sources: List[str],
        sinks: List[str],
        sanitizers: List[str],
        cwe: str,
        cwe_name: str,
        attack: str,
    ) -> str:
        """Format hypothesis text using template."""
        template = self.HYPOTHESIS_TEMPLATES.get(
            category,
            self.HYPOTHESIS_TEMPLATES["default"]
        )

        return template.format(
            sources=", ".join(sources) if sources else "external input",
            sinks=", ".join(sinks) if sinks else "sensitive operations",
            sanitizers=", ".join(sanitizers) if sanitizers else "proper validation",
            cwe=cwe,
            cwe_name=cwe_name,
            attack=attack,
        )

    def _deduplicate(
        self,
        hypotheses: List[SecurityHypothesis],
    ) -> List[SecurityHypothesis]:
        """Remove duplicate hypotheses based on key attributes."""
        seen: Set[Tuple] = set()
        unique = []

        for h in hypotheses:
            # Create a key from main attributes
            key = (
                tuple(sorted(h.cwe_ids)),
                tuple(sorted(h.sink_patterns[:3])),
                tuple(sorted(h.source_patterns[:3])),
                h.category,
            )

            if key not in seen:
                seen.add(key)
                unique.append(h)

        return unique

    def _filter_quality(
        self,
        hypotheses: List[SecurityHypothesis],
        min_sinks: int = 1,
        min_sources: int = 1,
    ) -> List[SecurityHypothesis]:
        """Filter out low-quality hypotheses."""
        return [
            h for h in hypotheses
            if len(h.sink_patterns) >= min_sinks
            and len(h.source_patterns) >= min_sources
            and h.cwe_ids  # Must have at least one CWE
        ]


def generate_postgresql_hypotheses(
    max_hypotheses: int = 50,
    include_cve_patterns: bool = True,
) -> HypothesisBatch:
    """Convenience function to generate hypotheses for PostgreSQL.

    Args:
        max_hypotheses: Maximum number of hypotheses
        include_cve_patterns: Include patterns for known CVEs

    Returns:
        HypothesisBatch ready for validation
    """
    generator = HypothesisGenerator()

    # Generate general C hypotheses
    hypotheses = generator.generate_hypotheses(
        language="C",
        max_hypotheses=max_hypotheses,
        categories=[
            "buffer_overflow",
            "command_injection",
            "pg_dump_injection",
            "spi_sql_injection",
            "statistics_disclosure",
        ],
    )

    # Add CVE-specific hypotheses
    if include_cve_patterns:
        for cve_id in ["CVE-2025-8713", "CVE-2025-8714", "CVE-2025-8715"]:
            cve_hypotheses = generator.generate_for_cve(cve_id)
            hypotheses.extend(cve_hypotheses)

    # Create batch
    return generator.create_batch(
        hypotheses=hypotheses,
        name="PostgreSQL Security Audit",
        target_project="postgresql-17.x",
        description="Hypothesis-driven security analysis targeting PostgreSQL 17.x vulnerabilities",
    )
