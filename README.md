# OpenRouter MCP Server

MCP (Model Context Protocol) server for discovering and querying 300+ AI models available on OpenRouter.

## Features

- **List models** — Browse all available models with pricing, context limits, and capabilities
- **Search & filter** — Find models by provider, price, context length, features (tools, vision, etc.)
- **Compare models** — Side-by-side comparison of multiple models
- **Get details** — Full metadata for any specific model
- **Cached responses** — 5-minute cache to reduce API calls

## Installation

```bash
pip install openrouter-mcp
```

## Usage

### With OpenClaw

Add to your `openclaw.json` MCP servers config:

```json
{
  "mcp": {
    "servers": {
      "openrouter-models": {
        "command": "openrouter-mcp",
        "env": {
          "OPENROUTER_API_KEY": "your-api-key"
        }
      }
    }
  }
}
```

Then restart the gateway. Agents can now use the MCP tools to query OpenRouter models.

> **Note:** `OPENROUTER_API_KEY` is optional but recommended for higher rate limits (200 req/min vs 20 req/min).
> Get your key at: https://openrouter.ai/keys

**Example agent usage:**

```python
# Agent can now call MCP tools like:
list_models(sort_by="context_length")
search_models(query="claude", max_input_price=5.0)
get_model(model_id="anthropic/claude-sonnet-4.6")
compare_models(model_ids="qwen/qwen3.6-plus,anthropic/claude-sonnet-4.6")
```

### Standalone (stdio)

```bash
export OPENROUTER_API_KEY=your-key
python -m openrouter_mcp.server
```

### Available Tools

| Tool | Description |
|------|-------------|
| `list_models` | List all models with optional modality filter and sorting |
| `get_model` | Get detailed info for a specific model by ID |
| `search_models` | Search and filter models by query, provider, price, context, features |
| `compare_models` | Compare multiple models side by side |
| `refresh_cache` | Force refresh the model cache from OpenRouter API |

## Examples

### List models sorted by context length

```json
{
  "name": "list_models",
  "arguments": {
    "modality": "text",
    "sort_by": "context_length"
  }
}
```

### Search for Claude models under $5/1M tokens

```json
{
  "name": "search_models",
  "arguments": {
    "query": "claude",
    "provider": "anthropic",
    "max_input_price": 5.0,
    "requires_tools": true
  }
}
```

### Compare 3 models

```json
{
  "name": "compare_models",
  "arguments": {
    "model_ids": "anthropic/claude-sonnet-4.6,qwen/qwen3.6-plus,openai/gpt-5.4"
  }
}
```

### Get model details

```json
{
  "name": "get_model",
  "arguments": {
    "model_id": "anthropic/claude-sonnet-4.6"
  }
}
```

## API Reference

### `list_models(modality, sort_by)`

- `modality` (str, default: "text"): Filter by output type. Options: `text`, `image`, `audio`, `embeddings`, `all`
- `sort_by` (str, default: "name"): Sort by: `name`, `created`, `price`, `context_length`

### `get_model(model_id)`

- `model_id` (str, required): Model slug, e.g. `anthropic/claude-sonnet-4.6`

### `search_models(query, provider, max_input_price, min_context, requires_tools, requires_vision, free_only)`

- `query` (str): Free-text search in model name/id/description
- `provider` (str): Filter by provider (e.g. `anthropic`, `google`, `openai`)
- `max_input_price` (float): Max input price per 1M tokens (0 = no limit)
- `min_context` (int): Minimum context window size
- `requires_tools` (bool): Only models supporting tool calling
- `requires_vision` (bool): Only models with vision/image input
- `free_only` (bool): Only free models

### `compare_models(model_ids)`

- `model_ids` (str, required): Comma-separated list of model IDs

### `refresh_cache()`

Force refresh the model cache from OpenRouter API.

## Rate Limits

- Without API key: 20 requests/minute
- With API key: 200 requests/minute
- Model data is cached for 5 minutes

Get your API key at: https://openrouter.ai/keys

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.
