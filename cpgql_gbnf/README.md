CPGQL GBNF Grammar
==================

This module defines the Code Property Graph Query Language (CPGQL) grammar in **GBNF**—an extended BNF format suitable for grammar-guided tooling such as XGrammar: https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md. The goal is to formalise the syntax of Joern traversals so that we can drive query generation, validation, or constrained decoding for LLMs.

Overview
--------

CPGQL queries are fluent graph traversals composed of:

1. A root object (`cpg`)
2. Node-type steps (e.g. `.method`, `.call`)
3. Filter, map, and repeat steps (Scala-style lambdas)
4. Property directives (e.g. `.name`, `.codeExact("planner")`)
5. Execution directives (`.l`, `.head`, `.toList`, etc.)
6. Augmentation directives (`newTagNode`, `store`, `run.commit`, …)

A simple example:

```scala
cpg.method.name.toList
```

This yields all method names by traversing from the graph root, selecting method nodes, projecting the `name` property, and materialising results as a list.

Grammar Source
--------------

- `docs/GBNF grammar for the CPGQL.md` — human-readable manuscript of the grammar.
- `cpgql_clean.gbnf` — sanitised grammar (comments removed, escapes normalised) ready for llama.cpp or other GBNF consumers.

Usage Scenarios
---------------

- **Query generation:** enforce syntactic correctness when generating CPGQL traversals automatically.
- **Static validation:** parse user-provided traversals before executing them against Joern.
- **Documentation tooling:** produce syntax-highlighted representations or query builders.
- **RAG integration:** constrain LLM decoding to valid grammar productions when emitting Joern queries.
- **llama.cpp integration:** load `cpgql_clean.gbnf` via `LlamaGrammar` to enforce grammar-guided sampling.

Using cpgql_clean.gbnf with llama.cpp (Python)
----------------------------------------------

```python
from pathlib import Path
from llama_cpp import Llama, LlamaGrammar

gbnf = Path("cpgql_clean.gbnf").read_text(encoding="utf-8")
llm = Llama(model_path="C:/path/to/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf", n_ctx=32768)
grammar = LlamaGrammar.from_string(gbnf)
response = llm.create_completion(prompt="...", grammar=grammar, max_tokens=512)
print(response["choices"][0]["text"])
```

Next Steps
----------

1. Keep `cpgql_clean.gbnf` in sync with updates to the canonical grammar source.
2. Derive a JSON Schema or AST model from the grammar to enable programmatic traversal building.
3. Extend the grammar with Joern-specific helper aliases (e.g. `.l` vs `.toList`) and module-specific extensions if needed.
4. Add automated tests that feed sample queries through a grammar engine, ensuring parity with Joern’s reference syntax.
