"""
Agent Migration Examples

Demonstrates how to migrate agents from hardcoded prompts to PromptRegistry.

Author: Week 4 - Agent Migration
Date: November 25, 2025

Usage:
    python examples/agent_migration_example.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_global_cpg_config, CPGConfig
from typing import Optional


# ============================================================================
# Example 1: Simple Agent - Before and After
# ============================================================================

print("\n" + "="*80)
print("Example 1: Simple Agent Migration")
print("="*80 + "\n")

# BEFORE: Hardcoded PostgreSQL prompts
class SimpleAgentBefore:
    """Simple agent with hardcoded prompts (OLD WAY)."""

    def __init__(self, llm=None):
        self.llm = llm
        self.system_prompt = """You are an expert PostgreSQL code analyst.

Your task is to analyze source code and provide insights."""

    def analyze(self, code):
        # Uses hardcoded "PostgreSQL expert" always
        prompt = f"""{self.system_prompt}

Code to analyze:
{code}
"""
        print("OLD WAY - System prompt:")
        print(self.system_prompt[:100] + "...")


# AFTER: Uses PromptRegistry
class SimpleAgentAfter:
    """Simple agent with PromptRegistry (NEW WAY)."""

    def __init__(self, llm=None, cpg_config: Optional[CPGConfig] = None):
        self.llm = llm

        # Get CPG config
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

        # Get analyst title from domain
        self.analyst_title = cpg_config.get_code_analyst_title()

        # Build system prompt using domain info
        self.system_prompt = f"""You are an expert {self.analyst_title}.

Your task is to analyze source code and provide insights."""

    def analyze(self, code):
        # Automatically adapts to domain
        prompt = f"""{self.system_prompt}

Code to analyze:
{code}
"""
        print("NEW WAY - System prompt:")
        print(self.system_prompt[:100] + "...")


# Demo
print("--- OLD WAY (Hardcoded PostgreSQL) ---")
old_agent = SimpleAgentBefore()
old_agent.analyze("some_code")

print("\n--- NEW WAY (Domain-Adaptive) ---")

# PostgreSQL domain
new_agent_pg = SimpleAgentAfter()
new_agent_pg.analyze("some_code")

# Linux Kernel domain
config_lk = CPGConfig()
config_lk.set_cpg_type("linux_kernel")
new_agent_lk = SimpleAgentAfter(cpg_config=config_lk)
new_agent_lk.analyze("some_code")


# ============================================================================
# Example 2: Agent with Multiple Prompts
# ============================================================================

print("\n\n" + "="*80)
print("Example 2: Agent with Multiple Prompts")
print("="*80 + "\n")

# BEFORE: Multiple hardcoded prompts
class ComplexAgentBefore:
    """Agent with multiple hardcoded prompts (OLD WAY)."""

    def __init__(self):
        self.system_prompt = "You are a PostgreSQL expert."
        self.error_prompt = "Explain this PostgreSQL error..."
        self.summary_prompt = "Summarize these PostgreSQL functions..."

    def show_prompts(self):
        print("OLD WAY - Multiple Hardcoded Prompts:")
        print(f"  System: {self.system_prompt}")
        print(f"  Error: {self.error_prompt}")
        print(f"  Summary: {self.summary_prompt}")


# AFTER: Gets prompts from registry
class ComplexAgentAfter:
    """Agent with PromptRegistry (NEW WAY)."""

    def __init__(self, cpg_config: Optional[CPGConfig] = None):
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

        # Get analyst title
        analyst = cpg_config.get_code_analyst_title()

        # Build prompts using domain info
        self.system_prompt = f"You are a {analyst}."

        # These could also come from PromptRegistry if defined in YAML
        self.error_prompt = f"As a {analyst}, explain this error..."
        self.summary_prompt = f"As a {analyst}, summarize these functions..."

    def show_prompts(self):
        print(f"NEW WAY - Domain: {self.cpg_config.cpg_type}")
        print(f"  System: {self.system_prompt}")
        print(f"  Error: {self.error_prompt}")
        print(f"  Summary: {self.summary_prompt}")


# Demo
print("--- OLD WAY ---")
old_complex = ComplexAgentBefore()
old_complex.show_prompts()

print("\n--- NEW WAY (PostgreSQL) ---")
new_complex_pg = ComplexAgentAfter()
new_complex_pg.show_prompts()

print("\n--- NEW WAY (Linux Kernel) ---")
lk_config = CPGConfig()
lk_config.set_cpg_type("linux_kernel")
new_complex_lk = ComplexAgentAfter(cpg_config=lk_config)
new_complex_lk.show_prompts()


# ============================================================================
# Example 3: Backward Compatible Migration
# ============================================================================

print("\n\n" + "="*80)
print("Example 3: Backward Compatible Migration")
print("="*80 + "\n")

class BackwardCompatibleAgent:
    """
    Agent that supports both old and new usage patterns.

    Old usage (still works):
        agent = BackwardCompatibleAgent()

    New usage (recommended):
        agent = BackwardCompatibleAgent(cpg_config=config)
    """

    def __init__(
        self,
        llm=None,
        cpg_config: Optional[CPGConfig] = None,
        # Deprecated parameter for old code
        use_hardcoded: bool = False
    ):
        self.llm = llm

        # NEW WAY: Try to use CPGConfig
        try:
            if cpg_config is None:
                cpg_config = get_global_cpg_config()
            self.cpg_config = cpg_config
            self.analyst_title = cpg_config.get_code_analyst_title()
            self.migration_status = "✅ Using PromptRegistry"
        except Exception as e:
            # OLD WAY: Fallback to hardcoded
            if use_hardcoded:
                self.cpg_config = None
                self.analyst_title = "PostgreSQL expert"
                self.migration_status = "⚠️  Using hardcoded prompts (fallback)"
            else:
                raise

    def show_status(self):
        print(f"Status: {self.migration_status}")
        print(f"Analyst Title: {self.analyst_title}")


# Demo
print("--- Old Usage Pattern (backward compatible) ---")
bc_agent1 = BackwardCompatibleAgent()
bc_agent1.show_status()

print("\n--- New Usage Pattern (recommended) ---")
config = CPGConfig()
config.set_cpg_type("llvm")
bc_agent2 = BackwardCompatibleAgent(cpg_config=config)
bc_agent2.show_status()


# ============================================================================
# Example 4: Real InterpreterAgent Usage
# ============================================================================

print("\n\n" + "="*80)
print("Example 4: Real InterpreterAgent Usage")
print("="*80 + "\n")

from src.agents.interpreter_agent import InterpreterAgent

# Create agent with different domains
print("--- PostgreSQL Domain ---")
pg_config = CPGConfig()
pg_config.set_cpg_type("postgresql")
interpreter_pg = InterpreterAgent(cpg_config=pg_config)
print(f"Domain: {interpreter_pg.cpg_config.cpg_type}")
print(f"Analyst Title: {interpreter_pg.code_analyst_title}")

print("\n--- Linux Kernel Domain ---")
lk_config = CPGConfig()
lk_config.set_cpg_type("linux_kernel")
interpreter_lk = InterpreterAgent(cpg_config=lk_config)
print(f"Domain: {interpreter_lk.cpg_config.cpg_type}")
print(f"Analyst Title: {interpreter_lk.code_analyst_title}")

print("\n--- Generic Domain ---")
gen_config = CPGConfig()
gen_config.set_cpg_type("generic")
interpreter_gen = InterpreterAgent(cpg_config=gen_config)
print(f"Domain: {interpreter_gen.cpg_config.cpg_type}")
print(f"Analyst Title: {interpreter_gen.code_analyst_title}")


# ============================================================================
# Summary
# ============================================================================

print("\n\n" + "="*80)
print("Migration Summary")
print("="*80 + "\n")

print("""
Key Takeaways:

1. Add cpg_config parameter to __init__():
   def __init__(self, ..., cpg_config: Optional[CPGConfig] = None):
       if cpg_config is None:
           cpg_config = get_global_cpg_config()

2. Get analyst title from config:
   self.analyst_title = cpg_config.get_code_analyst_title()

3. Use analyst title in prompts:
   prompt = f"You are an expert {self.analyst_title}."

4. For backward compatibility:
   - Keep old parameters with deprecation warnings
   - Add try/except with fallback to hardcoded

5. Test with multiple domains:
   - PostgreSQL
   - Linux Kernel
   - LLVM
   - Generic

Benefits:
✅ Agents automatically adapt to CPG domain
✅ Easy to add new domains (just edit YAML)
✅ Centralized prompt management
✅ Backward compatible with old code
""")

print("="*80)
print("All examples completed successfully!")
print("="*80 + "\n")
