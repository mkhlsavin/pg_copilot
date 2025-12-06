# Agent Migration Guide: Moving to PromptRegistry

**Date:** November 25, 2025
**Version:** 1.0
**Author:** Week 4 - Agent Migration

---

## Overview

This guide shows how to migrate ReAct agents from hardcoded prompts to PromptRegistry for domain-specific, configurable prompts.

### Benefits of Migration

- ✅ **Multi-domain support**: Agents automatically adapt to CPG domain (PostgreSQL, Linux Kernel, LLVM)
- ✅ **Centralized prompts**: All prompts in YAML files for easy editing
- ✅ **Version control**: Track prompt changes over time
- ✅ **A/B testing**: Easy to test different prompt versions
- ✅ **Backward compatible**: Old agents continue working

---

## Migration Steps

### Step 1: Add CPGConfig Parameter

**Before:**
```python
class MyAgent:
    def __init__(self, llm_interface=None):
        self.llm = llm_interface
```

**After:**
```python
from src.config import get_global_cpg_config, CPGConfig

class MyAgent:
    def __init__(self, llm_interface=None, cpg_config: Optional[CPGConfig] = None):
        self.llm = llm_interface

        # Get CPG config
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config
```

### Step 2: Get Prompts from Registry

**Before:**
```python
from src.generation.prompts import CPGQL_SYSTEM_PROMPT

class MyAgent:
    def __init__(self, llm_interface=None):
        self.system_prompt = CPGQL_SYSTEM_PROMPT  # Hardcoded PostgreSQL
```

**After:**
```python
class MyAgent:
    def __init__(self, llm_interface=None, cpg_config: Optional[CPGConfig] = None):
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

        # Get domain-specific prompt
        self.system_prompt = cpg_config.get_prompt("cpgql_generation_system")
        # Auto-adapts to PostgreSQL, Linux Kernel, LLVM, etc.
```

### Step 3: Use Domain-Specific Titles

**Before:**
```python
prompt = f"""You are an expert PostgreSQL code analyst.

{question}
"""
```

**After:**
```python
# Get analyst title from domain config
analyst_title = self.cpg_config.get_code_analyst_title()
# "PostgreSQL 17.6 expert" or "Linux Kernel 6.x expert"

prompt = f"""You are an expert {analyst_title}.

{question}
"""
```

### Step 4: Backward Compatibility (Optional)

Keep fallback for old code:

```python
class MyAgent:
    def __init__(
        self,
        llm_interface=None,
        cpg_config: Optional[CPGConfig] = None,
        # Old parameter for backward compatibility
        use_custom_prompt: bool = False
    ):
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

        # Try PromptRegistry first
        try:
            self.system_prompt = cpg_config.get_prompt("cpgql_generation_system")
        except:
            # Fallback to hardcoded (backward compatibility)
            if use_custom_prompt:
                from src.generation.prompts import CPGQL_SYSTEM_PROMPT
                self.system_prompt = CPGQL_SYSTEM_PROMPT
                logger.warning("Using hardcoded prompt (PromptRegistry not available)")
            else:
                raise
```

---

## Complete Example: InterpreterAgent

### Before (Week 3)

```python
class InterpreterAgent:
    def __init__(self, llm_interface=None):
        self.llm = llm_interface

    def _generate_llm_summary(self, question, ...):
        # Hardcoded PostgreSQL expert
        prompt = f"""You are an expert PostgreSQL code analyst.

Convert the CPGQL query results into a clear, informative answer.

Question: {question}
...
"""
        response = self.llm.generate_simple(prompt, ...)
```

### After (Week 4)

```python
from src.config import get_global_cpg_config, CPGConfig

class InterpreterAgent:
    def __init__(
        self,
        llm_interface=None,
        cpg_config: Optional[CPGConfig] = None
    ):
        self.llm = llm_interface

        # Get CPG config
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

        # Get analyst title from domain
        self.code_analyst_title = cpg_config.get_code_analyst_title()
        # "PostgreSQL 17.6 expert", "Linux Kernel 6.x expert", etc.

    def _generate_llm_summary(self, question, ...):
        # Domain-specific analyst title
        prompt = f"""You are an expert {self.code_analyst_title}.

Convert the CPGQL query results into a clear, informative answer.

Question: {question}
...
"""
        response = self.llm.generate_simple(prompt, ...)
```

**Result:**
- For PostgreSQL CPG: "You are an expert PostgreSQL 17.6 expert."
- For Linux Kernel CPG: "You are an expert Linux Kernel 6.x expert."
- Automatically adapts based on `cpg.type` in `config.yaml`

---

## Example: GeneratorAgent Migration

### Before

```python
from src.generation.prompts import build_cpgql_generation_prompt

class GeneratorAgent:
    def __init__(self, cpgql_generator):
        self.generator = cpgql_generator

    def generate(self, question, context):
        # Build prompt using hardcoded function
        system_prompt, user_prompt = build_cpgql_generation_prompt(
            question,
            context['similar_qa'],
            context['cpgql_examples']
        )

        # system_prompt is always PostgreSQL-specific
        query = self.generator.llm.generate_simple(
            prompt=system_prompt + "\n\n" + user_prompt
        )
```

### After

```python
from src.config import get_global_cpg_config, CPGConfig

class GeneratorAgent:
    def __init__(
        self,
        cpgql_generator,
        cpg_config: Optional[CPGConfig] = None
    ):
        self.generator = cpgql_generator

        # Get CPG config
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config

    def generate(self, question, context):
        # Get domain-specific system prompt from registry
        system_prompt = self.cpg_config.get_prompt(
            "cpgql_generation_system",
            version=self.cpg_config.domain_info.version_target
        )

        # Build user prompt (can still use helper or build directly)
        user_prompt = self._build_user_prompt(
            question,
            context['similar_qa'],
            context['cpgql_examples']
        )

        # Generate
        query = self.generator.llm.generate_simple(
            prompt=system_prompt + "\n\n" + user_prompt
        )

    def _build_user_prompt(self, question, similar_qa, cpgql_examples):
        """Build user prompt (domain-agnostic)."""
        # Format QA examples
        qa_text = "\n".join([
            f"Q: {qa['question']}\nA: {qa['answer']}"
            for qa in similar_qa[:3]
        ])

        # Format CPGQL examples
        examples_text = "\n".join([
            f"Input: {ex['input']}\nQuery: {ex['output']}"
            for ex in cpgql_examples[:5]
        ])

        return f"""Given the following context:

{qa_text}

And these CPGQL examples:

{examples_text}

Generate a CPGQL query for: {question}
"""
```

---

## Testing After Migration

### Test 1: Verify Domain Adaptation

```python
def test_agent_domain_adaptation():
    from src.agents.interpreter_agent import InterpreterAgent
    from src.config import CPGConfig

    # Test with PostgreSQL
    pg_config = CPGConfig()
    pg_config.set_cpg_type("postgresql")

    agent = InterpreterAgent(cpg_config=pg_config)
    assert "PostgreSQL" in agent.code_analyst_title

    # Test with Linux Kernel
    lk_config = CPGConfig()
    lk_config.set_cpg_type("linux_kernel")

    agent = InterpreterAgent(cpg_config=lk_config)
    assert "Linux Kernel" in agent.code_analyst_title
```

### Test 2: Verify Backward Compatibility

```python
def test_backward_compatibility():
    from src.agents.interpreter_agent import InterpreterAgent

    # Old usage (no cpg_config parameter)
    agent = InterpreterAgent(llm_interface=my_llm)

    # Should still work, uses global CPG config
    assert agent.cpg_config is not None
    assert agent.code_analyst_title is not None
```

---

## Adding New Domain Support

### 1. Add Prompts to cpg_domains.yaml

```yaml
domains:
  chromium:
    name: "Chromium"
    version_target: "120.x"

    metadata:
      code_analyst_title: "Chromium expert"

    prompts:
      cpgql_generation_system:
        template: |
          You are an expert in CPGQL for Chromium browser source code.

          Chromium CPG Schema:
          - Methods: Browser functions and IPC calls
          - Common patterns: Mojo interfaces, IPC messages
          ...

      code_analyst_title:
        template: "Chromium ${version} expert"
```

### 2. Use New Domain

```python
config = get_global_cpg_config()
config.set_cpg_type("chromium")

# All agents automatically adapt
agent = InterpreterAgent()
# Now uses Chromium-specific prompts
```

**No code changes needed!**

---

## Common Pitfalls

### Pitfall 1: Forgetting to Pass cpg_config

❌ **Wrong:**
```python
class MyAgent:
    def __init__(self, llm):
        # Forgot to add cpg_config parameter
        self.llm = llm
        self.prompt = cpg_config.get_prompt("...")  # NameError!
```

✅ **Correct:**
```python
class MyAgent:
    def __init__(self, llm, cpg_config: Optional[CPGConfig] = None):
        self.llm = llm
        if cpg_config is None:
            cpg_config = get_global_cpg_config()
        self.cpg_config = cpg_config
```

### Pitfall 2: Hardcoding Domain Names

❌ **Wrong:**
```python
prompt = f"""You are a PostgreSQL expert."""  # Hardcoded!
```

✅ **Correct:**
```python
analyst_title = self.cpg_config.get_code_analyst_title()
prompt = f"""You are an expert {analyst_title}."""
```

### Pitfall 3: Not Handling Missing Prompts

❌ **Wrong:**
```python
prompt = config.get_prompt("nonexistent_prompt")
# Returns "[ERROR: Prompt 'nonexistent_prompt' not found]"
```

✅ **Correct:**
```python
try:
    prompt = config.get_prompt("my_prompt")
except Exception:
    # Fallback to hardcoded
    from src.generation.prompts import MY_FALLBACK_PROMPT
    prompt = MY_FALLBACK_PROMPT
```

---

## Migration Checklist

For each agent:

- [ ] Add `cpg_config` parameter to `__init__()`
- [ ] Get `cpg_config` with fallback to global: `get_global_cpg_config()`
- [ ] Replace hardcoded prompts with `cpg_config.get_prompt()`
- [ ] Use `cpg_config.get_code_analyst_title()` instead of "PostgreSQL expert"
- [ ] Add backward compatibility fallback (optional)
- [ ] Update tests to test with multiple domains
- [ ] Update documentation

---

## Summary

**Key Changes:**
1. Add `cpg_config: Optional[CPGConfig] = None` to agent `__init__()`
2. Use `cpg_config.get_prompt("prompt_name")` instead of hardcoded prompts
3. Use `cpg_config.get_code_analyst_title()` for domain-specific titles
4. Test with multiple domains

**Benefits:**
- Agents automatically adapt to CPG domain
- Easy to add new domains (just edit YAML)
- Centralized prompt management
- Backward compatible

**Example Agents:**
- ✅ `InterpreterAgent` - Migrated in Week 4
- 🔄 `GeneratorAgent` - Migration in progress
- ⏳ `RetrieverAgent` - To be migrated
- ⏳ `AnalyzerAgent` - To be migrated
- ⏳ `EnrichmentAgent` - To be migrated

---

**Happy Migrating!** 🚀

For questions, see `WEEK4_AGENT_MIGRATION_COMPLETE.md`
