from pathlib import Path

from xgrammar_tests.grammar_loader import load_grammar
from xgrammar_tests.sampler import SamplerConfig, build_sampler

spec = load_grammar()
print('engine present', spec.engine is not None)
config = SamplerConfig(
    tokenizer_vocab=Path('data/qwen25_vocab.txt'),
    tokenizer_metadata=Path('data/qwen25_metadata.json'),
)
print('config enabled', config.enabled)
try:
    sampler = build_sampler(spec, config)
    print('sampler type:', type(sampler))
except Exception:
    import traceback
    traceback.print_exc()
