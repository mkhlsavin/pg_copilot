# Integrations

> Third-party service integrations for CodeGraph.

## Available Integrations

| Integration | Description |
|-------------|-------------|
| [Yandex AI Studio](./YANDEX_AI_STUDIO.md) | Yandex Cloud AI Studio (YandexGPT, Qwen3) via OpenAI-compatible API |
| [GigaChat](./GIGACHAT.md) | Sber GigaChat LLM integration |

## Adding New Integrations

New integrations should:
1. Implement the base provider interface from `src/llm/base_provider.py`
2. Add configuration to `config.yaml`
3. Document in this folder

## Related Documentation

- [LLM Configuration](../getting-started/CONFIGURATION.md)
- [Security](../reference/SECURITY.md) - DLP and audit for LLM providers
