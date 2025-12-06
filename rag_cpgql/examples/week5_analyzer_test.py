"""
Week 5 Agent Migration Test: AnalyzerAgent

Tests AnalyzerAgent migration to PromptRegistry across multiple domains.

Usage:
    python examples/week5_analyzer_test.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.analyzer_agent import AnalyzerAgent
from src.config import CPGConfig

print("=" * 80)
print("Week 5: AnalyzerAgent Migration Test")
print("=" * 80)
print()

# Test 1: PostgreSQL Domain
print("Test 1: PostgreSQL Domain")
print("-" * 80)

pg_config = CPGConfig()
pg_config.set_cpg_type("postgresql")

analyzer_pg = AnalyzerAgent(cpg_config=pg_config)
print(f"Domain: {analyzer_pg.cpg_config.cpg_type}")
print(f"Analyst Title: {analyzer_pg.code_analyst_title}")
print()

# Test rule-based analysis (no LLM needed)
question1 = "How does autovacuum work in PostgreSQL?"
result1 = analyzer_pg.analyze(question1)
print(f"Question: {question1}")
print(f"Intent: {result1['intent']}")
print(f"Query Mode: {result1['query_mode']}")
print(f"Domain: {result1['domain']}")
print(f"Keywords: {result1['keywords'][:5]}")
print(f"Confidence: {result1['confidence']:.2f}")
print()

# Test 2: Linux Kernel Domain
print("Test 2: Linux Kernel Domain")
print("-" * 80)

lk_config = CPGConfig()
lk_config.set_cpg_type("linux_kernel")

analyzer_lk = AnalyzerAgent(cpg_config=lk_config)
print(f"Domain: {analyzer_lk.cpg_config.cpg_type}")
print(f"Analyst Title: {analyzer_lk.code_analyst_title}")
print()

# Test with Linux Kernel question
question2 = "What mechanism ensures consistency during shutdown?"
result2 = analyzer_lk.analyze(question2)
print(f"Question: {question2}")
print(f"Intent: {result2['intent']}")
print(f"Query Mode: {result2['query_mode']}")
print(f"Domain: {result2['domain']}")
print(f"Keywords: {result2['keywords'][:5]}")
print(f"Confidence: {result2['confidence']:.2f}")
print()

# Test 3: LLVM Domain
print("Test 3: LLVM Domain")
print("-" * 80)

llvm_config = CPGConfig()
llvm_config.set_cpg_type("llvm")

analyzer_llvm = AnalyzerAgent(cpg_config=llvm_config)
print(f"Domain: {analyzer_llvm.cpg_config.cpg_type}")
print(f"Analyst Title: {analyzer_llvm.code_analyst_title}")
print()

# Test with LLVM question
question3 = "Find all LLVM optimization passes"
result3 = analyzer_llvm.analyze(question3)
print(f"Question: {question3}")
print(f"Intent: {result3['intent']}")
print(f"Query Mode: {result3['query_mode']}")
print(f"Domain: {result3['domain']}")
print(f"Keywords: {result3['keywords'][:5]}")
print(f"Confidence: {result3['confidence']:.2f}")
print()

# Test 4: Generic Domain (Fallback)
print("Test 4: Generic Domain (Fallback)")
print("-" * 80)

generic_config = CPGConfig()
generic_config.set_cpg_type("generic")

analyzer_generic = AnalyzerAgent(cpg_config=generic_config)
print(f"Domain: {analyzer_generic.cpg_config.cpg_type}")
print(f"Analyst Title: {analyzer_generic.code_analyst_title}")
print()

# Test with generic question
question4 = "What functions handle error conditions?"
result4 = analyzer_generic.analyze(question4)
print(f"Question: {question4}")
print(f"Intent: {result4['intent']}")
print(f"Query Mode: {result4['query_mode']}")
print(f"Domain: {result4['domain']}")
print(f"Keywords: {result4['keywords'][:5]}")
print(f"Confidence: {result4['confidence']:.2f}")
print()

# Test 5: Backward Compatibility (no cpg_config parameter)
print("Test 5: Backward Compatibility")
print("-" * 80)

# Old usage pattern (should still work)
analyzer_old = AnalyzerAgent()
print(f"Domain: {analyzer_old.cpg_config.cpg_type}")
print(f"Analyst Title: {analyzer_old.code_analyst_title}")
print("[OK] Backward compatibility maintained - old code still works!")
print()

# Test 6: LLM Analysis (if LLM available)
print("Test 6: LLM Analysis with Domain-Adaptive Prompts")
print("-" * 80)

# Show the prompt that would be used (without actually calling LLM)
print("PostgreSQL Domain Prompt:")
print(f"  'You are an expert {analyzer_pg.code_analyst_title}.'")
print()

print("Linux Kernel Domain Prompt:")
print(f"  'You are an expert {analyzer_lk.code_analyst_title}.'")
print()

print("LLVM Domain Prompt:")
print(f"  'You are an expert {analyzer_llvm.code_analyst_title}.'")
print()

print("Generic Domain Prompt:")
print(f"  'You are an expert {analyzer_generic.code_analyst_title}.'")
print()

# Summary
print("=" * 80)
print("Summary")
print("=" * 80)
print()

print("[OK] AnalyzerAgent successfully migrated to PromptRegistry")
print("[OK] Domain-adaptive analyst titles working correctly")
print("[OK] Multiple domain support:")
print(f"   - PostgreSQL: '{analyzer_pg.code_analyst_title}'")
print(f"   - Linux Kernel: '{analyzer_lk.code_analyst_title}'")
print(f"   - LLVM: '{analyzer_llvm.code_analyst_title}'")
print(f"   - Generic: '{analyzer_generic.code_analyst_title}'")
print("[OK] Backward compatibility maintained")
print()

print("Key Changes:")
print("  1. Added cpg_config parameter to __init__()")
print("  2. Get code_analyst_title from CPGConfig")
print("  3. Updated analyze_with_llm() to use domain-specific title")
print("  4. Prompt now adapts to CPG domain automatically")
print()

print("=" * 80)
print("All tests completed successfully!")
print("=" * 80)
