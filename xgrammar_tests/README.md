# xgrammar_tests

Prototype playground for generating Code Property Graph Query Language (CPGQL) traversals using the formal grammar defined in `../cpgql_gbnf/cpgql_clean.gbnf` and the [XGrammar](https://xgrammar.mlc.ai/docs/) library.

## Quick Start

```bash
conda activate llama.cpp

# Optional: create/activate a local venv if you are not relying solely on the conda env.
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .[dev]

# Generate three random queries
xgrammar-generate --count 3
```

The implementation targets Python 3.11+. Grammar-driven tests live in `tests/`.

> **Note:** XGrammar requires a sampler backed by an LLM/tokenizer to emit strings.  
> The current CLI loads and sanitises `cpgql_clean.gbnf`, compiles it into an XGrammar `Grammar`, and is ready to plug into a model-backed sampler. Until a sampler is registered (e.g. via `GrammarCompiler` with tokenizer metadata), `xgrammar-generate` will report that no sampler API is available.

### Optional: Supplying Tokenizer Metadata

If you have precomputed tokenizer information (vocabulary + metadata JSON produced via `TokenizerInfo.serialize_json`), you can point the CLI at those files to compile a sampler:

```bash
xgrammar-generate \
  --count 5 \
  --tokenizer-vocab path/to/vocab.txt \
  --tokenizer-metadata path/to/tokenizer_metadata.json
# or use a GGUF model directly
xgrammar-generate \
  --count 5 \
  --tokenizer-gguf C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf
```

When both files are provided, the CLI invokes `GrammarCompiler` to produce a sampler compatible with the grammar, enabling actual query generation. Without these inputs, the command still validates the grammar but refrains from sampling.

The helper script `tools/export_tokenizer_metadata.py` can produce the required files from a Hugging Face tokenizer:

```bash
conda run -n llama.cpp python tools/export_tokenizer_metadata.py \
  C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  --vocab tokenizer.vocab.txt \
  --metadata tokenizer.metadata.json
```

Once exported, pass the generated files to `xgrammar-generate` via `--tokenizer-vocab` and `--tokenizer-metadata`.

### Joern End-to-End Smoke Test

To generate queries and submit them to a running Joern server, use the helper script:

```bash
python tools/run_joern_e2e.py \
  --tokenizer-gguf C:/Users/user/.lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  --count 5 \
  --connect \
  --joern-load
```

The script attempts to connect to `localhost:8080` (configurable via `--joern-host`/`--joern-port`), generates queries with the GGUF-backed sampler, validates them, and prints Joern responses when the server is reachable.
