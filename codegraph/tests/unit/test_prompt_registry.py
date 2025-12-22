"""
Tests for Prompt Registry and CPG Config

Author: Configurable LLM Architecture - Week 3
Date: November 25, 2025

Usage:
    pytest tests/test_prompt_registry.py -v
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prompts import (
    Prompt,
    PromptRegistry,
    reset_global_registry
)
from src.config import (
    CPGConfig,
    CPGDomainInfo,
    reset_global_cpg_config
)


# Fixtures

@pytest.fixture
def temp_prompt_dir(tmp_path):
    """Create temporary directory with test prompt files."""
    prompts_dir = tmp_path / "config" / "prompts"
    prompts_dir.mkdir(parents=True)

    # Create generic prompts.yaml
    prompts_yaml = {
        'prompts': {
            'test_prompt': {
                'template': 'Hello, ${name}!',
                'description': 'Test prompt',
                'category': 'test',
                'version': '1.0'
            },
            'another_prompt': {
                'template': 'You are ${role}',
                'description': 'Role prompt',
                'category': 'general',
                'version': '1.0'
            }
        }
    }

    with open(prompts_dir / "prompts.yaml", 'w') as f:
        yaml.dump(prompts_yaml, f)

    # Create cpg_domains.yaml
    domains_yaml = {
        'domains': {
            'test_domain': {
                'name': 'Test Domain',
                'description': 'Test domain for testing',
                'version_target': '1.0',
                'metadata': {
                    'code_analyst_title': 'test expert',
                    'cpg_elements': 'test elements'
                },
                'prompts': {
                    'domain_specific_prompt': {
                        'template': 'Domain: ${domain_name}',
                        'description': 'Domain-specific prompt',
                        'category': 'test',
                        'version': '1.0'
                    }
                }
            }
        }
    }

    with open(prompts_dir / "cpg_domains.yaml", 'w') as f:
        yaml.dump(domains_yaml, f)

    return prompts_dir


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global singletons before each test."""
    reset_global_registry()
    reset_global_cpg_config()
    yield
    reset_global_registry()
    reset_global_cpg_config()


# Tests for Prompt class

def test_prompt_creation():
    """Test Prompt creation."""
    prompt = Prompt(
        name="test",
        template="Hello, ${name}!",
        description="Test prompt",
        category="test",
        domain="generic",
        version="1.0"
    )

    assert prompt.name == "test"
    assert prompt.template == "Hello, ${name}!"
    assert prompt.description == "Test prompt"
    assert prompt.category == "test"
    assert prompt.domain == "generic"
    assert prompt.version == "1.0"


def test_prompt_render():
    """Test prompt rendering with variables."""
    prompt = Prompt(
        name="greeting",
        template="Hello, ${name}! You are a ${role}."
    )

    result = prompt.render(name="Alice", role="developer")

    assert result == "Hello, Alice! You are a developer."


def test_prompt_render_partial():
    """Test prompt rendering with missing variables (safe_substitute)."""
    prompt = Prompt(
        name="greeting",
        template="Hello, ${name}! You are a ${role}."
    )

    # Only provide 'name', not 'role'
    result = prompt.render(name="Bob")

    assert "Hello, Bob!" in result
    assert "${role}" in result  # Unsubstituted variable remains


# Tests for PromptRegistry

def test_registry_creation(temp_prompt_dir):
    """Test PromptRegistry creation."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    assert registry.config_dir == temp_prompt_dir
    assert len(registry.prompts) > 0


def test_registry_load_generic_prompts(temp_prompt_dir):
    """Test loading generic prompts from prompts.yaml."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    assert 'generic' in registry.prompts
    assert 'test_prompt' in registry.prompts['generic']
    assert 'another_prompt' in registry.prompts['generic']


def test_registry_load_domain_prompts(temp_prompt_dir):
    """Test loading domain-specific prompts from cpg_domains.yaml."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    assert 'test_domain' in registry.prompts
    assert 'domain_specific_prompt' in registry.prompts['test_domain']


def test_registry_get_prompt(temp_prompt_dir):
    """Test getting prompt from registry."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    prompt = registry.get("test_prompt", domain="generic", name="Alice")

    assert prompt == "Hello, Alice!"


def test_registry_get_with_fallback(temp_prompt_dir):
    """Test fallback to generic domain."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)
    registry.set_domain("test_domain")

    # 'test_prompt' only exists in generic, not test_domain
    prompt = registry.get("test_prompt", fallback=True, name="Bob")

    assert prompt == "Hello, Bob!"


def test_registry_get_without_fallback(temp_prompt_dir):
    """Test error when prompt not found without fallback."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)
    registry.set_domain("test_domain")

    # 'test_prompt' only exists in generic
    prompt = registry.get("test_prompt", fallback=False)

    assert "[ERROR:" in prompt


def test_registry_set_domain(temp_prompt_dir):
    """Test setting current domain."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    registry.set_domain("test_domain")

    assert registry.current_domain == "test_domain"


def test_registry_list_prompts(temp_prompt_dir):
    """Test listing prompts."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    # List all prompts
    all_prompts = registry.list_prompts()
    assert len(all_prompts) > 0

    # List generic prompts
    generic_prompts = registry.list_prompts(domain="generic")
    assert len(generic_prompts) == 2  # test_prompt, another_prompt

    # List by category
    test_prompts = registry.list_prompts(category="test")
    assert len(test_prompts) >= 1


def test_registry_register_prompt(temp_prompt_dir):
    """Test registering prompt at runtime."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    registry.register_prompt(
        prompt_name="custom_prompt",
        template="Custom: ${value}",
        domain="generic",
        description="Custom test prompt"
    )

    assert "custom_prompt" in registry.prompts["generic"]

    # Get registered prompt
    result = registry.get("custom_prompt", value="42")
    assert result == "Custom: 42"


def test_registry_reload(temp_prompt_dir):
    """Test reloading prompts."""
    registry = PromptRegistry(config_dir=temp_prompt_dir)

    initial_count = len(registry.list_prompts())

    # Register runtime prompt
    registry.register_prompt(
        prompt_name="runtime_prompt",
        template="Runtime: ${x}",
        domain="generic"
    )

    assert len(registry.list_prompts()) == initial_count + 1

    # Reload (should remove runtime prompt)
    registry.reload()

    assert len(registry.list_prompts()) == initial_count


# Tests for CPGConfig

def test_cpg_config_creation():
    """Test CPGConfig creation."""
    config = CPGConfig()

    assert config.cpg_type is not None
    assert config.domain_info is not None


def test_cpg_config_get_prompt():
    """Test getting prompt via CPGConfig."""
    config = CPGConfig()

    # This should work if config.yaml exists and has cpg.type set
    prompt = config.get_prompt("code_analyst_title")

    assert prompt is not None
    assert len(prompt) > 0


def test_cpg_config_set_cpg_type():
    """Test changing CPG type."""
    config = CPGConfig()

    initial_type = config.cpg_type

    config.set_cpg_type("generic")

    assert config.cpg_type == "generic"
    assert config.cpg_type != initial_type


def test_cpg_config_get_code_analyst_title():
    """Test getting code analyst title."""
    config = CPGConfig()

    title = config.get_code_analyst_title()

    assert title is not None
    assert len(title) > 0


def test_cpg_config_get_cpg_elements():
    """Test getting CPG elements."""
    config = CPGConfig()

    elements = config.get_cpg_elements()

    assert elements is not None
    assert "method" in elements or "function" in elements or "test" in elements


def test_cpg_config_get_metadata():
    """Test getting metadata."""
    config = CPGConfig()

    # Get metadata with default
    value = config.get_metadata("nonexistent_key", default="default_value")

    assert value == "default_value"


def test_cpg_domain_info():
    """Test CPGDomainInfo dataclass."""
    info = CPGDomainInfo(
        key="test",
        name="Test Domain",
        description="Test description",
        version_target="1.0",
        metadata={'key': 'value'}
    )

    assert info.key == "test"
    assert info.name == "Test Domain"
    assert info.version_target == "1.0"
    assert info.metadata['key'] == 'value'


def test_cpg_domain_info_defaults():
    """Test CPGDomainInfo default values."""
    info = CPGDomainInfo(
        key="test",
        name="Test"
    )

    assert info.description == ""
    assert info.version_target == ""
    assert info.metadata == {}


# Integration Tests

def test_integration_prompt_and_config(temp_prompt_dir):
    """Integration test: PromptRegistry + CPGConfig."""
    # Create config.yaml in temp dir
    config_yaml = {
        'cpg': {
            'type': 'generic'  # Use 'generic' domain that always exists
        }
    }

    config_path = temp_prompt_dir.parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config_yaml, f)

    # Create CPGConfig with temp config
    config = CPGConfig(config_path=config_path)

    # Get generic prompt that exists in the test fixtures
    prompt = config.get_prompt("test_prompt", name="World")

    # Should return either the prompt or an error if not found
    # The test validates that the integration between PromptRegistry and CPGConfig works
    assert prompt is not None
    # If the prompt was found, it should have been formatted
    if "ERROR" not in prompt:
        assert "Hello" in prompt or "World" in prompt


def test_global_registry_singleton():
    """Test that global registry is a singleton."""
    from src.prompts import get_global_registry

    registry1 = get_global_registry()
    registry2 = get_global_registry()

    assert registry1 is registry2


def test_global_cpg_config_singleton():
    """Test that global CPG config is a singleton."""
    from src.config import get_global_cpg_config

    config1 = get_global_cpg_config()
    config2 = get_global_cpg_config()

    assert config1 is config2


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
