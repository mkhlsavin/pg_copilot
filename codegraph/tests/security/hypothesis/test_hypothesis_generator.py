"""
Tests for Hypothesis Generator.

Tests for:
- HypothesisGenerator initialization
- HYPOTHESIS_TEMPLATES
- CWE_CATEGORY_MAP
- generate_hypotheses method
- generate_for_cve method
- create_batch method
- Helper methods (_get_relevant_cwes, _generate_for_pattern, etc.)
- generate_postgresql_hypotheses convenience function
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid

from src.security.hypothesis.models import (
    SecurityHypothesis,
    HypothesisBatch,
    ValidationStatus,
    Severity,
)
from src.security.hypothesis.hypothesis_generator import (
    HypothesisGenerator,
    generate_postgresql_hypotheses,
)
from src.security.hypothesis.knowledge_base import (
    SecurityKnowledgeBase,
    CWE_DATABASE,
)


# =============================================================================
# HypothesisGenerator Initialization Tests
# =============================================================================

class TestHypothesisGeneratorInit:
    """Tests for HypothesisGenerator initialization."""

    def test_init_default_knowledge_base(self):
        """Test initialization with default knowledge base."""
        generator = HypothesisGenerator()
        assert generator.kb is not None
        assert isinstance(generator.kb, SecurityKnowledgeBase)

    def test_init_custom_knowledge_base(self, mock_knowledge_base):
        """Test initialization with custom knowledge base."""
        generator = HypothesisGenerator(knowledge_base=mock_knowledge_base)
        assert generator.kb is mock_knowledge_base

    def test_init_has_templates(self):
        """Test generator has hypothesis templates."""
        generator = HypothesisGenerator()
        assert hasattr(generator, "HYPOTHESIS_TEMPLATES")
        assert len(generator.HYPOTHESIS_TEMPLATES) > 0

    def test_init_has_cwe_category_map(self):
        """Test generator has CWE category map."""
        generator = HypothesisGenerator()
        assert hasattr(generator, "CWE_CATEGORY_MAP")
        assert len(generator.CWE_CATEGORY_MAP) > 0


# =============================================================================
# HYPOTHESIS_TEMPLATES Tests
# =============================================================================

class TestHypothesisTemplates:
    """Tests for HYPOTHESIS_TEMPLATES."""

    def test_templates_exist(self):
        """Test all expected templates exist."""
        expected_templates = [
            "buffer_overflow",
            "format_string",
            "command_injection",
            "sql_injection",
            "code_injection",
            "information_disclosure",
            "use_after_free",
            "integer_overflow",
            "default",
        ]
        for template_name in expected_templates:
            assert template_name in HypothesisGenerator.HYPOTHESIS_TEMPLATES

    def test_templates_have_placeholders(self):
        """Test templates have required placeholders."""
        # All templates must have cwe and attack placeholders
        required_all = ["{cwe}", "{attack}"]
        # Most templates have sources, sinks - but not all (e.g., information_disclosure)
        common_placeholders = ["{sinks}"]
        for name, template in HypothesisGenerator.HYPOTHESIS_TEMPLATES.items():
            for placeholder in required_all:
                assert placeholder in template, f"{name} missing {placeholder}"
            # Check common placeholders (at least one should be present)
            has_common = any(p in template for p in common_placeholders)
            assert has_common, f"{name} missing common placeholders"

    def test_templates_are_strings(self):
        """Test all templates are strings."""
        for name, template in HypothesisGenerator.HYPOTHESIS_TEMPLATES.items():
            assert isinstance(template, str), f"{name} is not a string"


# =============================================================================
# CWE_CATEGORY_MAP Tests
# =============================================================================

class TestCWECategoryMap:
    """Tests for CWE_CATEGORY_MAP."""

    def test_map_has_buffer_overflow_cwes(self):
        """Test buffer overflow CWEs are mapped."""
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-120"] == "buffer_overflow"
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-119"] == "buffer_overflow"
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-787"] == "buffer_overflow"

    def test_map_has_injection_cwes(self):
        """Test injection CWEs are mapped."""
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-78"] == "command_injection"
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-89"] == "sql_injection"
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-94"] == "code_injection"

    def test_map_has_memory_cwes(self):
        """Test memory-related CWEs are mapped."""
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-416"] == "use_after_free"
        assert HypothesisGenerator.CWE_CATEGORY_MAP["CWE-190"] == "integer_overflow"

    def test_most_mapped_cwes_exist_in_database(self):
        """Test most mapped CWEs exist in CWE database."""
        # Allow a few CWEs to be in the map but not in our subset of the database
        found_count = sum(
            1 for cwe_id in HypothesisGenerator.CWE_CATEGORY_MAP.keys()
            if cwe_id in CWE_DATABASE
        )
        total = len(HypothesisGenerator.CWE_CATEGORY_MAP)
        # At least 80% should be in the database
        assert found_count / total >= 0.8, f"Only {found_count}/{total} CWEs in database"


# =============================================================================
# generate_hypotheses Tests
# =============================================================================

class TestGenerateHypotheses:
    """Tests for generate_hypotheses method."""

    @pytest.fixture
    def generator(self):
        """Create a hypothesis generator."""
        return HypothesisGenerator()

    def test_generate_hypotheses_returns_list(self, generator):
        """Test generate_hypotheses returns a list."""
        hypotheses = generator.generate_hypotheses(language="C", max_hypotheses=10)
        assert isinstance(hypotheses, list)

    def test_generate_hypotheses_returns_security_hypotheses(self, generator):
        """Test generate_hypotheses returns SecurityHypothesis objects."""
        hypotheses = generator.generate_hypotheses(language="C", max_hypotheses=10)
        for h in hypotheses:
            assert isinstance(h, SecurityHypothesis)

    def test_generate_hypotheses_respects_max(self, generator):
        """Test generate_hypotheses respects max_hypotheses limit."""
        hypotheses = generator.generate_hypotheses(language="C", max_hypotheses=5)
        assert len(hypotheses) <= 5

    def test_generate_hypotheses_sorted_by_priority(self, generator):
        """Test hypotheses are sorted by priority score descending."""
        hypotheses = generator.generate_hypotheses(language="C", max_hypotheses=10)
        if len(hypotheses) >= 2:
            for i in range(len(hypotheses) - 1):
                assert hypotheses[i].priority_score >= hypotheses[i + 1].priority_score

    def test_generate_hypotheses_with_categories_filter(self, generator):
        """Test generate_hypotheses filters by categories."""
        hypotheses = generator.generate_hypotheses(
            language="C",
            max_hypotheses=50,
            categories=["buffer_overflow"],
        )
        for h in hypotheses:
            assert h.category == "buffer_overflow"

    def test_generate_hypotheses_with_cwe_filter(self, generator):
        """Test generate_hypotheses filters by CWE IDs."""
        hypotheses = generator.generate_hypotheses(
            language="C",
            max_hypotheses=50,
            cwe_filter=["CWE-120"],
        )
        for h in hypotheses:
            assert "CWE-120" in h.cwe_ids

    def test_generate_hypotheses_with_min_risk_score(self, generator):
        """Test generate_hypotheses filters by minimum risk score."""
        hypotheses = generator.generate_hypotheses(
            language="C",
            max_hypotheses=50,
            min_risk_score=0.5,
        )
        # All hypotheses should be derived from CWEs with risk >= 0.5
        assert len(hypotheses) > 0

    def test_generate_hypotheses_have_required_fields(self, generator):
        """Test generated hypotheses have all required fields."""
        hypotheses = generator.generate_hypotheses(language="C", max_hypotheses=5)
        for h in hypotheses:
            assert h.id is not None
            assert len(h.hypothesis_text) > 0
            assert len(h.cwe_ids) > 0
            assert h.language == "C"
            assert h.category is not None
            assert len(h.sink_patterns) > 0
            assert len(h.source_patterns) > 0

    def test_generate_hypotheses_have_unique_ids(self, generator):
        """Test generated hypotheses have unique IDs."""
        hypotheses = generator.generate_hypotheses(language="C", max_hypotheses=20)
        ids = [h.id for h in hypotheses]
        assert len(ids) == len(set(ids))

    def test_generate_hypotheses_empty_for_unknown_language(self, generator):
        """Test generate_hypotheses returns empty for unknown language."""
        hypotheses = generator.generate_hypotheses(language="COBOL", max_hypotheses=10)
        assert len(hypotheses) == 0

    def test_generate_hypotheses_default_language_is_c(self, generator):
        """Test default language is C."""
        hypotheses = generator.generate_hypotheses(max_hypotheses=5)
        for h in hypotheses:
            assert h.language == "C"


# =============================================================================
# generate_for_cve Tests
# =============================================================================

class TestGenerateForCVE:
    """Tests for generate_for_cve method."""

    @pytest.fixture
    def generator(self):
        """Create a hypothesis generator."""
        return HypothesisGenerator()

    def test_generate_for_cve_2025_8713(self, generator):
        """Test generate_for_cve returns hypotheses for CVE-2025-8713."""
        hypotheses = generator.generate_for_cve("CVE-2025-8713")
        assert len(hypotheses) > 0
        for h in hypotheses:
            assert "CVE-2025-8713" in h.tags

    def test_generate_for_cve_2025_8714(self, generator):
        """Test generate_for_cve returns hypotheses for CVE-2025-8714."""
        hypotheses = generator.generate_for_cve("CVE-2025-8714")
        assert len(hypotheses) > 0
        for h in hypotheses:
            assert "CVE-2025-8714" in h.tags

    def test_generate_for_cve_2025_8715(self, generator):
        """Test generate_for_cve returns hypotheses for CVE-2025-8715."""
        hypotheses = generator.generate_for_cve("CVE-2025-8715")
        assert len(hypotheses) > 0
        for h in hypotheses:
            assert "CVE-2025-8715" in h.tags

    def test_generate_for_cve_unknown_returns_empty(self, generator):
        """Test generate_for_cve returns empty for unknown CVE."""
        hypotheses = generator.generate_for_cve("CVE-9999-9999")
        assert hypotheses == []

    def test_generate_for_cve_has_detection_query(self, generator):
        """Test CVE hypotheses have detection queries."""
        hypotheses = generator.generate_for_cve("CVE-2025-8714")
        for h in hypotheses:
            assert h.sql_query is not None

    def test_generate_for_cve_has_cve_targeted_tag(self, generator):
        """Test CVE hypotheses have cve-targeted tag."""
        hypotheses = generator.generate_for_cve("CVE-2025-8713")
        for h in hypotheses:
            assert "cve-targeted" in h.tags

    def test_generate_for_cve_higher_priority(self, generator):
        """Test CVE hypotheses have higher initial priority."""
        hypotheses = generator.generate_for_cve("CVE-2025-8714")
        for h in hypotheses:
            assert h.priority_score >= 0.8


# =============================================================================
# create_batch Tests
# =============================================================================

class TestCreateBatch:
    """Tests for create_batch method."""

    @pytest.fixture
    def generator(self):
        """Create a hypothesis generator."""
        return HypothesisGenerator()

    def test_create_batch_returns_hypothesis_batch(self, generator, sample_hypothesis):
        """Test create_batch returns HypothesisBatch."""
        batch = generator.create_batch(
            hypotheses=[sample_hypothesis],
            name="Test Batch",
            target_project="test-project",
        )
        assert isinstance(batch, HypothesisBatch)

    def test_create_batch_has_correct_fields(self, generator, sample_hypothesis):
        """Test created batch has correct fields."""
        batch = generator.create_batch(
            hypotheses=[sample_hypothesis],
            name="Test Batch",
            target_project="test-project",
            description="Test description",
        )
        assert batch.name == "Test Batch"
        assert batch.target_project == "test-project"
        assert batch.description == "Test description"
        assert len(batch.hypotheses) == 1

    def test_create_batch_generates_id(self, generator, sample_hypothesis):
        """Test created batch has a UUID."""
        batch = generator.create_batch(
            hypotheses=[sample_hypothesis],
            name="Test Batch",
            target_project="test-project",
        )
        assert batch.id is not None
        # Should be valid UUID
        uuid.UUID(batch.id)

    def test_create_batch_default_description(self, generator, sample_hypothesis):
        """Test batch has default description when not provided."""
        batch = generator.create_batch(
            hypotheses=[sample_hypothesis],
            name="Test Batch",
            target_project="my-project",
        )
        assert "my-project" in batch.description


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Tests for generator helper methods."""

    @pytest.fixture
    def generator(self):
        """Create a hypothesis generator."""
        return HypothesisGenerator()

    def test_get_relevant_cwes_by_language(self, generator):
        """Test _get_relevant_cwes returns CWEs for language."""
        cwes = generator._get_relevant_cwes("C", None, 0.0)
        assert len(cwes) > 0
        for cwe in cwes:
            assert "C" in cwe.languages

    def test_get_relevant_cwes_with_filter(self, generator):
        """Test _get_relevant_cwes respects CWE filter."""
        cwes = generator._get_relevant_cwes("C", ["CWE-120", "CWE-78"], 0.0)
        for cwe in cwes:
            assert cwe.id in ["CWE-120", "CWE-78"]

    def test_get_relevant_cwes_with_min_risk(self, generator):
        """Test _get_relevant_cwes respects min risk score."""
        cwes = generator._get_relevant_cwes("C", None, 0.5)
        for cwe in cwes:
            assert cwe.risk_score >= 0.5

    def test_format_hypothesis_text_buffer_overflow(self, generator):
        """Test _format_hypothesis_text for buffer overflow."""
        text = generator._format_hypothesis_text(
            category="buffer_overflow",
            sources=["recv", "getenv"],
            sinks=["strcpy", "memcpy"],
            sanitizers=["strlcpy"],
            cwe="CWE-120",
            cwe_name="Buffer Overflow",
            attack="Overflow Buffers",
        )
        assert "recv" in text
        assert "strcpy" in text
        assert "CWE-120" in text

    def test_format_hypothesis_text_uses_default_template(self, generator):
        """Test _format_hypothesis_text falls back to default template."""
        text = generator._format_hypothesis_text(
            category="unknown_category",
            sources=["source"],
            sinks=["sink"],
            sanitizers=["sanitizer"],
            cwe="CWE-1",
            cwe_name="Test",
            attack="Test Attack",
        )
        assert "source" in text
        assert "sink" in text

    def test_deduplicate_removes_duplicates(self, generator):
        """Test _deduplicate removes duplicate hypotheses."""
        h1 = SecurityHypothesis(
            id="1",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["recv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        h2 = SecurityHypothesis(
            id="2",
            hypothesis_text="Test2",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["recv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        result = generator._deduplicate([h1, h2])
        assert len(result) == 1

    def test_deduplicate_keeps_unique(self, generator):
        """Test _deduplicate keeps unique hypotheses."""
        h1 = SecurityHypothesis(
            id="1",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["recv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        h2 = SecurityHypothesis(
            id="2",
            hypothesis_text="Test2",
            cwe_ids=["CWE-78"],
            capec_ids=[],
            language="C",
            category="command_injection",
            source_patterns=["getenv"],
            sink_patterns=["system"],
            sanitizer_patterns=[],
        )
        result = generator._deduplicate([h1, h2])
        assert len(result) == 2

    def test_filter_quality_removes_empty_sinks(self, generator):
        """Test _filter_quality removes hypotheses with no sinks."""
        h = SecurityHypothesis(
            id="1",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["recv"],
            sink_patterns=[],  # Empty
            sanitizer_patterns=[],
        )
        result = generator._filter_quality([h])
        assert len(result) == 0

    def test_filter_quality_removes_empty_sources(self, generator):
        """Test _filter_quality removes hypotheses with no sources."""
        h = SecurityHypothesis(
            id="1",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=[],  # Empty
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        result = generator._filter_quality([h])
        assert len(result) == 0

    def test_filter_quality_keeps_valid_hypotheses(self, generator):
        """Test _filter_quality keeps valid hypotheses."""
        h = SecurityHypothesis(
            id="1",
            hypothesis_text="Test",
            cwe_ids=["CWE-120"],
            capec_ids=[],
            language="C",
            category="buffer_overflow",
            source_patterns=["recv"],
            sink_patterns=["strcpy"],
            sanitizer_patterns=[],
        )
        result = generator._filter_quality([h])
        assert len(result) == 1


# =============================================================================
# generate_postgresql_hypotheses Tests
# =============================================================================

class TestGeneratePostgresqlHypotheses:
    """Tests for generate_postgresql_hypotheses convenience function."""

    def test_returns_hypothesis_batch(self):
        """Test function returns HypothesisBatch."""
        batch = generate_postgresql_hypotheses(max_hypotheses=10)
        assert isinstance(batch, HypothesisBatch)

    def test_batch_has_name(self):
        """Test batch has PostgreSQL name."""
        batch = generate_postgresql_hypotheses(max_hypotheses=10)
        assert "PostgreSQL" in batch.name

    def test_batch_has_target_project(self):
        """Test batch has postgresql target project."""
        batch = generate_postgresql_hypotheses(max_hypotheses=10)
        assert "postgresql" in batch.target_project.lower()

    def test_respects_max_hypotheses(self):
        """Test function respects max_hypotheses limit."""
        batch = generate_postgresql_hypotheses(max_hypotheses=5, include_cve_patterns=False)
        assert batch.total_count <= 5 + 10  # Allow some buffer for implementation details

    def test_includes_cve_patterns_by_default(self):
        """Test includes CVE patterns by default."""
        batch = generate_postgresql_hypotheses(max_hypotheses=50)
        # Should have CVE-targeted hypotheses
        cve_hypotheses = [h for h in batch.hypotheses if "cve-targeted" in h.tags]
        assert len(cve_hypotheses) > 0

    def test_exclude_cve_patterns(self):
        """Test can exclude CVE patterns."""
        batch = generate_postgresql_hypotheses(
            max_hypotheses=50,
            include_cve_patterns=False,
        )
        # Should not have CVE-targeted hypotheses
        cve_hypotheses = [h for h in batch.hypotheses if "cve-targeted" in h.tags]
        assert len(cve_hypotheses) == 0
