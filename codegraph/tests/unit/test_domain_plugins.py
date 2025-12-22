"""
Unit tests for the Domain Plugin System.

Tests the domain plugin base class, registry, and specific plugins.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.domains.base import DomainPlugin, SubsystemInfo, SecurityPattern, IntentPattern
from src.domains.registry import DomainRegistry
from src.domains.generic_cpp import GenericCppDomainPlugin, generic_cpp_plugin


class TestSubsystemInfo:
    """Tests for SubsystemInfo dataclass."""

    def test_create_subsystem_info(self):
        """Test creating a SubsystemInfo instance."""
        info = SubsystemInfo(
            name="Test Subsystem",
            description="A test subsystem",
            key_functions=["func1", "func2"],
            patterns=[r"^test_.*$"],
            related_files=["test.h"]
        )
        assert info.name == "Test Subsystem"
        assert info.description == "A test subsystem"
        assert len(info.key_functions) == 2
        assert len(info.patterns) == 1
        assert len(info.related_files) == 1

    def test_subsystem_info_defaults(self):
        """Test SubsystemInfo default values."""
        info = SubsystemInfo(name="Minimal", description="Minimal subsystem")
        assert info.key_functions == []
        assert info.patterns == []
        assert info.related_files == []


class TestSecurityPattern:
    """Tests for SecurityPattern dataclass."""

    def test_create_security_pattern(self):
        """Test creating a SecurityPattern instance."""
        pattern = SecurityPattern(
            id="test_vuln",
            name="Test Vulnerability",
            description="A test vulnerability",
            severity="high",
            cwe_id="CWE-123",
            indicators=["dangerous_func"],
            sinks=["sink_func"],
            sources=["user_input"],
            sanitizers=["validate"]
        )
        assert pattern.id == "test_vuln"
        assert pattern.severity == "high"
        assert pattern.cwe_id == "CWE-123"

    def test_security_pattern_defaults(self):
        """Test SecurityPattern default values."""
        pattern = SecurityPattern(
            id="minimal",
            name="Minimal",
            description="Minimal pattern",
            severity="low"
        )
        assert pattern.cwe_id is None
        assert pattern.indicators == []
        assert pattern.sinks == []


class TestIntentPattern:
    """Tests for IntentPattern dataclass."""

    def test_create_intent_pattern(self):
        """Test creating an IntentPattern instance."""
        pattern = IntentPattern(
            intent_id="test_intent",
            keywords=["test", "check"],
            patterns=[r"test\s+.*"],
            examples=["test the code"],
            priority=5
        )
        assert pattern.intent_id == "test_intent"
        assert len(pattern.keywords) == 2
        assert pattern.priority == 5

    def test_intent_pattern_defaults(self):
        """Test IntentPattern default values."""
        pattern = IntentPattern(intent_id="minimal")
        assert pattern.keywords == []
        assert pattern.patterns == []
        assert pattern.examples == []
        assert pattern.priority == 0


class TestGenericCppPlugin:
    """Tests for GenericCppDomainPlugin."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh plugin instance."""
        return GenericCppDomainPlugin()

    def test_plugin_name(self, plugin):
        """Test plugin name property."""
        assert plugin.name == "generic_cpp"

    def test_plugin_display_name(self, plugin):
        """Test plugin display name property."""
        assert plugin.display_name == "C/C++"

    def test_plugin_description(self, plugin):
        """Test plugin description property."""
        assert "C/C++" in plugin.description

    def test_subsystems_loaded(self, plugin):
        """Test that subsystems are loaded correctly."""
        subsystems = plugin.subsystems
        assert len(subsystems) > 0
        assert "memory_management" in subsystems
        assert "file_io" in subsystems
        assert "string_handling" in subsystems

    def test_memory_management_subsystem(self, plugin):
        """Test memory management subsystem content."""
        mem = plugin.subsystems.get("memory_management")
        assert mem is not None
        assert "malloc" in mem.key_functions
        assert "free" in mem.key_functions
        assert "memcpy" in mem.key_functions

    def test_security_patterns_loaded(self, plugin):
        """Test that security patterns are loaded."""
        patterns = plugin.get_security_patterns()
        assert len(patterns) >= 5

        # Check for critical patterns
        pattern_ids = [p.id for p in patterns]
        assert "buffer_overflow" in pattern_ids
        assert "use_after_free" in pattern_ids
        assert "format_string" in pattern_ids

    def test_buffer_overflow_pattern(self, plugin):
        """Test buffer overflow pattern details."""
        patterns = plugin.get_security_patterns()
        buffer_overflow = next((p for p in patterns if p.id == "buffer_overflow"), None)
        assert buffer_overflow is not None
        assert buffer_overflow.severity == "critical"
        assert buffer_overflow.cwe_id == "CWE-120"
        assert "strcpy" in buffer_overflow.sinks

    def test_intent_patterns_loaded(self, plugin):
        """Test that intent patterns are loaded."""
        patterns = plugin.get_intent_patterns()
        assert len(patterns) >= 3
        assert "security" in patterns
        assert "performance" in patterns

    def test_prompts_loaded(self, plugin):
        """Test that prompts are loaded."""
        prompts = plugin.get_prompts()
        assert len(prompts) >= 3
        assert "security" in prompts
        assert "performance" in prompts
        assert "system" in prompts["security"]
        assert "user_template" in prompts["security"]

    def test_get_subsystem_functions(self, plugin):
        """Test get_subsystem_functions method."""
        funcs = plugin.get_subsystem_functions("memory_management")
        assert "malloc" in funcs
        assert "free" in funcs

    def test_get_subsystem_functions_unknown(self, plugin):
        """Test get_subsystem_functions with unknown subsystem."""
        funcs = plugin.get_subsystem_functions("nonexistent")
        assert funcs == []

    def test_get_all_key_functions(self, plugin):
        """Test get_all_key_functions method."""
        all_funcs = plugin.get_all_key_functions()
        assert len(all_funcs) > 20
        assert "malloc" in all_funcs
        assert "fopen" in all_funcs
        assert "strlen" in all_funcs

    def test_find_subsystem_for_function(self, plugin):
        """Test find_subsystem_for_function method."""
        assert plugin.find_subsystem_for_function("malloc") == "memory_management"
        assert plugin.find_subsystem_for_function("fopen") == "file_io"
        assert plugin.find_subsystem_for_function("strlen") == "string_handling"
        assert plugin.find_subsystem_for_function("unknown_func") is None

    def test_validate_function(self, plugin):
        """Test validate_function method."""
        assert plugin.validate_function("malloc") is True
        assert plugin.validate_function("fopen") is True
        assert plugin.validate_function("unknown_xyz") is False

    def test_get_expert_role(self, plugin):
        """Test get_expert_role method."""
        role = plugin.get_expert_role()
        assert "C/C++" in role
        assert "expert" in role

    def test_get_domain_context(self, plugin):
        """Test get_domain_context method."""
        context = plugin.get_domain_context()
        assert "C/C++" in context


class TestDomainRegistry:
    """Tests for DomainRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before and after each test."""
        DomainRegistry.clear()
        yield
        DomainRegistry.clear()

    def test_register_plugin(self):
        """Test registering a plugin."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        assert DomainRegistry.is_registered("generic_cpp")

    def test_list_domains(self):
        """Test listing registered domains."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        domains = DomainRegistry.list_domains()
        assert "generic_cpp" in domains

    def test_get_plugin(self):
        """Test getting a specific plugin."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        retrieved = DomainRegistry.get("generic_cpp")
        assert retrieved is not None
        assert retrieved.name == "generic_cpp"

    def test_get_nonexistent_plugin(self):
        """Test getting a nonexistent plugin returns None."""
        result = DomainRegistry.get("nonexistent")
        assert result is None

    def test_activate_plugin(self):
        """Test activating a plugin."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        activated = DomainRegistry.activate("generic_cpp")
        assert activated.name == "generic_cpp"
        assert DomainRegistry.get_active().name == "generic_cpp"

    def test_activate_nonexistent_raises(self):
        """Test that activating nonexistent plugin raises ValueError."""
        with pytest.raises(ValueError):
            DomainRegistry.activate("nonexistent")

    def test_get_active_when_none(self):
        """Test get_active when no plugin is activated."""
        with pytest.raises(RuntimeError):
            DomainRegistry.get_active()

    def test_get_active_or_none(self):
        """Test get_active_or_none returns None when not set."""
        result = DomainRegistry.get_active_or_none()
        assert result is None

    def test_unregister_plugin(self):
        """Test unregistering a plugin."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        assert DomainRegistry.is_registered("generic_cpp")

        result = DomainRegistry.unregister("generic_cpp")
        assert result is True
        assert not DomainRegistry.is_registered("generic_cpp")

    def test_unregister_active_plugin(self):
        """Test unregistering the active plugin clears active."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        DomainRegistry.activate("generic_cpp")

        DomainRegistry.unregister("generic_cpp")
        assert DomainRegistry.get_active_or_none() is None

    def test_set_default_domain(self):
        """Test setting the default domain."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)
        DomainRegistry.set_default("generic_cpp")

        # get_active should activate the default
        active = DomainRegistry.get_active()
        assert active.name == "generic_cpp"

    def test_get_all(self):
        """Test getting all registered plugins."""
        plugin = GenericCppDomainPlugin()
        DomainRegistry.register(plugin)

        all_plugins = DomainRegistry.get_all()
        assert len(all_plugins) == 1
        assert "generic_cpp" in all_plugins


class TestModuleLevelInstance:
    """Test the module-level plugin instance."""

    def test_generic_cpp_plugin_instance(self):
        """Test that generic_cpp_plugin is a valid instance."""
        assert generic_cpp_plugin is not None
        assert isinstance(generic_cpp_plugin, GenericCppDomainPlugin)
        assert generic_cpp_plugin.name == "generic_cpp"


class TestGenericCppPluginEnhancements:
    """Tests for new GenericCppDomainPlugin methods added in P1 refactoring."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh plugin instance."""
        return GenericCppDomainPlugin()

    def test_get_sanitization_patterns(self, plugin):
        """Test get_sanitization_patterns returns valid patterns."""
        patterns = plugin.get_sanitization_patterns()
        assert len(patterns) >= 10

        # Check structure
        for p in patterns:
            assert "name" in p
            assert "confidence" in p
            assert 0.0 <= p["confidence"] <= 1.0

        # Check expected patterns exist
        names = [p["name"] for p in patterns]
        assert "strncpy" in names
        assert "snprintf" in names
        assert "bounds_check" in names

    def test_get_memory_functions(self, plugin):
        """Test get_memory_functions returns memory function mappings."""
        mem = plugin.get_memory_functions()
        assert "allocate" in mem
        assert "free" in mem
        assert "copy" in mem

        # Check allocate functions
        assert "malloc" in mem["allocate"]
        assert "calloc" in mem["allocate"]
        assert "new" in mem["allocate"]

        # Check free functions
        assert "free" in mem["free"]
        assert "delete" in mem["free"]

    def test_get_lock_functions(self, plugin):
        """Test get_lock_functions returns lock primitives."""
        locks = plugin.get_lock_functions()
        assert len(locks) >= 10

        # Check for pthread and other lock primitives
        assert "pthread_mutex_lock" in locks
        assert "pthread_mutex_unlock" in locks
        assert "pthread_spin_lock" in locks


class TestPostgreSQLPlugin:
    """Tests for PostgreSQLDomainPlugin."""

    @pytest.fixture
    def plugin(self):
        """Create a fresh PostgreSQL plugin instance."""
        from src.domains.postgresql.plugin import PostgreSQLDomainPlugin
        return PostgreSQLDomainPlugin()

    def test_plugin_name(self, plugin):
        """Test plugin name property."""
        assert plugin.name == "postgresql"

    def test_plugin_display_name(self, plugin):
        """Test plugin display name property."""
        assert plugin.display_name == "PostgreSQL"

    def test_plugin_description(self, plugin):
        """Test plugin description property."""
        assert "PostgreSQL" in plugin.description

    def test_subsystems_loaded(self, plugin):
        """Test that subsystems are loaded correctly."""
        subsystems = plugin.subsystems
        assert len(subsystems) >= 8
        assert "executor" in subsystems
        assert "parser" in subsystems
        assert "optimizer" in subsystems
        assert "storage" in subsystems

    def test_executor_subsystem(self, plugin):
        """Test executor subsystem content."""
        executor = plugin.subsystems.get("executor")
        assert executor is not None
        assert "ExecProcNode" in executor.key_functions
        assert "backend/executor" in executor.patterns

    def test_get_expert_role(self, plugin):
        """Test get_expert_role method."""
        role = plugin.get_expert_role()
        assert "PostgreSQL" in role
        assert "expert" in role

    def test_get_domain_context(self, plugin):
        """Test get_domain_context method."""
        context = plugin.get_domain_context()
        assert "PostgreSQL" in context

    def test_get_entry_point_patterns(self, plugin):
        """Test get_entry_point_patterns method."""
        patterns = plugin.get_entry_point_patterns()
        assert len(patterns) >= 5
        assert "PG_FUNCTION_INFO_V1" in patterns
        assert "PostgresMain" in patterns

    def test_get_sensitive_functions(self, plugin):
        """Test get_sensitive_functions method."""
        funcs = plugin.get_sensitive_functions()
        assert "SPI_execute" in funcs
        assert "pg_read_file" in funcs

    def test_get_memory_functions(self, plugin):
        """Test get_memory_functions method for PostgreSQL."""
        mem = plugin.get_memory_functions()
        assert "allocate" in mem
        assert "free" in mem
        assert "palloc" in mem["allocate"]
        assert "pfree" in mem["free"]

    def test_get_lock_functions(self, plugin):
        """Test get_lock_functions method for PostgreSQL."""
        locks = plugin.get_lock_functions()
        assert len(locks) >= 4
        assert "LWLockAcquire" in locks
        assert "LWLockRelease" in locks

    def test_get_error_handling_patterns(self, plugin):
        """Test get_error_handling_patterns method."""
        patterns = plugin.get_error_handling_patterns()
        assert "error_macros" in patterns
        assert "elog" in patterns["error_macros"]
        assert "ereport" in patterns["error_macros"]

    def test_get_sanitization_confidence(self, plugin):
        """Test get_sanitization_confidence method returns valid patterns."""
        patterns = plugin.get_sanitization_confidence()
        assert len(patterns) >= 15

        # Check PostgreSQL-specific patterns
        assert "pg_escape_string" in patterns
        assert "SPI_prepare" in patterns
        assert "PQprepare" in patterns

        # Check confidence scores
        assert patterns["SPI_prepare"] == 1.0  # Prepared statements = highest
        assert patterns["pg_escape_string"] >= 0.8  # Escaping = high

    def test_get_sanitization_patterns(self, plugin):
        """Test get_sanitization_patterns method returns valid patterns."""
        patterns = plugin.get_sanitization_patterns()
        assert len(patterns) >= 6

        # Check structure
        for p in patterns:
            assert "name" in p
            assert "confidence" in p

        # Check expected patterns
        names = [p["name"] for p in patterns]
        assert "pg_escape_string" in names
        assert "SPI_prepare" in names


class TestSanitizationPatternMerging:
    """Test that sanitization patterns are properly merged from domain plugins."""

    @pytest.fixture(autouse=True)
    def setup_domain_and_clear_cache(self):
        """Ensure PostgreSQL domain is active and cache is cleared."""
        # Clear the sanitization pattern cache
        import src.analysis.dataflow_tracer as dt
        dt._cached_sanitization_patterns = None

        # Ensure PostgreSQL is active
        from src.domains.postgresql.plugin import PostgreSQLDomainPlugin
        DomainRegistry.register(PostgreSQLDomainPlugin())
        DomainRegistry.activate("postgresql")
        yield
        # Clean up
        dt._cached_sanitization_patterns = None

    def test_dataflow_tracer_loads_merged_patterns(self):
        """Test that dataflow_tracer merges generic + domain patterns."""
        from src.analysis.dataflow_tracer import get_sanitization_patterns

        patterns = get_sanitization_patterns()

        # Should have both generic (41) AND PostgreSQL (20) patterns
        # Some overlap expected, so total >= 55
        assert len(patterns) >= 55

        # Check generic patterns exist
        assert "parameterize" in patterns
        assert "prepare" in patterns
        assert "escape_%" in patterns

        # Check PostgreSQL patterns exist (from active domain plugin)
        assert "pg_escape_string" in patterns
        assert "SPI_prepare" in patterns

    def test_backwards_compat_sanitization_confidence(self):
        """Test backwards compatibility for SANITIZATION_CONFIDENCE access."""
        from src.analysis.dataflow_tracer import SANITIZATION_CONFIDENCE

        # Should work like a dictionary
        assert "prepare" in SANITIZATION_CONFIDENCE
        assert SANITIZATION_CONFIDENCE.get("prepare") == 1.0
        # Merged patterns: 41 generic + 20 PostgreSQL (with some overlap)
        assert len(SANITIZATION_CONFIDENCE) >= 55
        assert len(list(SANITIZATION_CONFIDENCE.keys())) >= 55


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
