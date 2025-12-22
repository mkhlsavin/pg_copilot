"""
Prompt Registry Examples

Демонстрирует использование PromptRegistry и CPGConfig для работы с промптами.

Author: Configurable LLM Architecture - Week 3
Date: November 25, 2025

Usage:
    python examples/prompt_registry_examples.py --example basic
    python examples/prompt_registry_examples.py --example postgresql
    python examples/prompt_registry_examples.py --example switch_domain
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prompts import get_global_registry
from src.config import get_global_cpg_config, CPGConfig


def example_1_basic_usage():
    """Example 1: Basic PromptRegistry usage."""
    print("\n" + "="*80)
    print("Example 1: Basic PromptRegistry Usage")
    print("="*80 + "\n")

    # Get global registry
    registry = get_global_registry()

    # Get generic prompt
    interpretation_prompt = registry.get(
        "interpretation_system",
        fallback=True
    )

    print("Generic interpretation prompt:")
    print(interpretation_prompt[:200] + "...")
    print()

    # Get prompt with variables
    error_prompt = registry.get(
        "error_explanation_user",
        query="cpg.method.name.l",
        error_message="Syntax error: unexpected token"
    )

    print("Error explanation prompt with variables:")
    print(error_prompt)
    print()

    print("✓ Example 1 completed!")


def example_2_postgresql_domain():
    """Example 2: PostgreSQL domain-specific prompts."""
    print("\n" + "="*80)
    print("Example 2: PostgreSQL Domain-Specific Prompts")
    print("="*80 + "\n")

    # Get CPG config (automatically sets domain to PostgreSQL from config.yaml)
    cpg_config = get_global_cpg_config()

    print(f"Current domain: {cpg_config.cpg_type}")
    print(f"Domain name: {cpg_config.domain_info.name}")
    print(f"Version target: {cpg_config.domain_info.version_target}")
    print()

    # Get PostgreSQL-specific prompt
    cpgql_prompt = cpg_config.get_prompt(
        "cpgql_generation_system",
        version="17.6"
    )

    print("PostgreSQL CPGQL generation prompt (first 500 chars):")
    print(cpgql_prompt[:500] + "...")
    print()

    # Get code analyst title
    analyst_title = cpg_config.get_code_analyst_title()
    print(f"Code analyst title: {analyst_title}")
    print()

    # Get CPG elements
    cpg_elements = cpg_config.get_cpg_elements()
    print(f"CPG elements: {cpg_elements}")
    print()

    print("✓ Example 2 completed!")


def example_3_switch_domain():
    """Example 3: Switch between CPG domains."""
    print("\n" + "="*80)
    print("Example 3: Switch Between CPG Domains")
    print("="*80 + "\n")

    cpg_config = get_global_cpg_config()

    # Show current domain
    print(f"Initial domain: {cpg_config.cpg_type}")
    print()

    # Get PostgreSQL prompt
    pg_prompt = cpg_config.get_prompt("code_analyst_title")
    print(f"PostgreSQL analyst: {pg_prompt}")
    print()

    # Switch to Linux Kernel
    cpg_config.set_cpg_type("linux_kernel")
    print(f"Switched to: {cpg_config.cpg_type}")

    # Get Linux Kernel prompt
    lk_prompt = cpg_config.get_prompt("code_analyst_title", version="6.x")
    print(f"Linux Kernel analyst: {lk_prompt}")
    print()

    # Get Linux Kernel query examples
    lk_examples = cpg_config.get_prompt("cpgql_examples")
    print("Linux Kernel query examples (first 300 chars):")
    print(lk_examples[:300] + "...")
    print()

    # Switch to LLVM
    cpg_config.set_cpg_type("llvm")
    print(f"Switched to: {cpg_config.cpg_type}")

    llvm_prompt = cpg_config.get_prompt("code_analyst_title", version="17.x")
    print(f"LLVM analyst: {llvm_prompt}")
    print()

    # Switch back to PostgreSQL
    cpg_config.set_cpg_type("postgresql")
    print(f"Switched back to: {cpg_config.cpg_type}")
    print()

    print("✓ Example 3 completed!")


def example_4_list_prompts():
    """Example 4: List available prompts."""
    print("\n" + "="*80)
    print("Example 4: List Available Prompts")
    print("="*80 + "\n")

    registry = get_global_registry()

    # List all prompts in PostgreSQL domain
    pg_prompts = registry.list_prompts(domain="postgresql")
    print(f"PostgreSQL domain prompts ({len(pg_prompts)}):")
    for prompt in pg_prompts:
        print(f"  - {prompt.name} ({prompt.category}): {prompt.description[:60]}...")
    print()

    # List all generic prompts
    generic_prompts = registry.list_prompts(domain="generic")
    print(f"Generic prompts ({len(generic_prompts)}):")
    for prompt in generic_prompts:
        print(f"  - {prompt.name} ({prompt.category}): {prompt.description[:60]}...")
    print()

    # List prompts by category
    generation_prompts = registry.list_prompts(category="generation")
    print(f"Generation prompts ({len(generation_prompts)}):")
    for prompt in generation_prompts:
        print(f"  - [{prompt.domain}] {prompt.name}")
    print()

    print("✓ Example 4 completed!")


def example_5_custom_prompt():
    """Example 5: Register custom prompt at runtime."""
    print("\n" + "="*80)
    print("Example 5: Register Custom Prompt")
    print("="*80 + "\n")

    registry = get_global_registry()

    # Register custom prompt
    registry.register_prompt(
        prompt_name="custom_greeting",
        template="Hello, ${name}! You are analyzing ${domain} code with ${tool}.",
        domain="generic",
        description="Custom greeting prompt",
        category="general"
    )

    # Use custom prompt
    greeting = registry.get(
        "custom_greeting",
        name="Alice",
        domain="PostgreSQL",
        tool="CPGQL"
    )

    print("Custom prompt result:")
    print(greeting)
    print()

    print("✓ Example 5 completed!")


def example_6_fallback_behavior():
    """Example 6: Prompt fallback behavior."""
    print("\n" + "="*80)
    print("Example 6: Prompt Fallback Behavior")
    print("="*80 + "\n")

    registry = get_global_registry()

    # Try to get prompt that only exists in generic
    registry.set_domain("linux_kernel")

    print("Current domain: linux_kernel")
    print()

    # This prompt only exists in generic domain
    prompt = registry.get(
        "interpretation_system",
        fallback=True  # Will fallback to generic
    )

    print("Got 'interpretation_system' (exists in generic, not linux_kernel):")
    print(prompt[:150] + "...")
    print()

    # Try without fallback
    prompt_no_fallback = registry.get(
        "interpretation_system",
        fallback=False  # Will not fallback
    )

    if "[ERROR:" in prompt_no_fallback:
        print("Without fallback: Got error message")
        print(prompt_no_fallback)
    print()

    print("✓ Example 6 completed!")


def main():
    """Run examples based on command line argument."""
    import argparse

    parser = argparse.ArgumentParser(description="Prompt Registry Examples")
    parser.add_argument(
        '--example',
        choices=['basic', 'postgresql', 'switch_domain', 'list', 'custom', 'fallback', 'all'],
        default='all',
        help='Which example to run'
    )

    args = parser.parse_args()

    try:
        if args.example == 'basic' or args.example == 'all':
            example_1_basic_usage()

        if args.example == 'postgresql' or args.example == 'all':
            example_2_postgresql_domain()

        if args.example == 'switch_domain' or args.example == 'all':
            example_3_switch_domain()

        if args.example == 'list' or args.example == 'all':
            example_4_list_prompts()

        if args.example == 'custom' or args.example == 'all':
            example_5_custom_prompt()

        if args.example == 'fallback' or args.example == 'all':
            example_6_fallback_behavior()

        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
