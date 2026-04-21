#!/usr/bin/env python3
"""
MCP Server: OpenRouter Models Discovery

Exposes OpenRouter's model catalog as MCP tools so agents can:
- List all 300+ models with pricing, capabilities, context limits
- Search/filter by provider, price, context, features
- Get detailed info on any specific model
- Compare multiple models side by side
"""

import asyncio
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
OR_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OR_MODELS_URL = "https://openrouter.ai/api/v1/models"

# In-memory cache
_cache: dict = {"data": None, "ts": 0.0}
CACHE_TTL = 300  # 5 minutes

mcp = FastMCP("openrouter-models")


# ── API Helper ──────────────────────────────────────────────────────────────

def fetch_models(force=False) -> list[dict]:
    """Fetch model list from OpenRouter with caching."""
    now = time.time()
    if _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL and not force:
        return _cache["data"]

    headers = {"Accept": "application/json"}
    if OR_API_KEY:
        headers["Authorization"] = f"Bearer {OR_API_KEY}"

    req = Request(OR_MODELS_URL, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            _cache["data"] = body.get("data", [])
            _cache["ts"] = now
            return _cache["data"]
    except URLError as e:
        raise RuntimeError(f"Failed to fetch OpenRouter models: {e}")


def _price_str(per_token: float) -> str:
    if per_token <= 0:
        return "free"
    return f"${per_token * 1_000_000:.2f}/1M tok"


def _format_model(m: dict, detail=False) -> str:
    pricing = m.get("pricing", {})
    input_p = float(pricing.get("prompt", 0))
    output_p = float(pricing.get("completion", 0))
    ctx = m.get("context_length", "?")
    name = m.get("name", m["id"])
    provider = m["id"].split("/")[0]
    supported = m.get("supported_parameters", [])

    lines = [
        f"**{m['id']}**",
        f"  Provider: {provider} | Context: {ctx:,}" if isinstance(ctx, (int, float)) else f"  Provider: {provider} | Context: {ctx}",
        f"  Pricing — Input: {_price_str(input_p)} | Output: {_price_str(output_p)}",
    ]
    if supported:
        lines.append(f"  Features: {', '.join(supported)}")
    if detail and m.get("description"):
        lines.append(f"  {m['description'][:150]}")
    if detail and m.get("architecture", {}).get("modality"):
        lines.append(f"  Modality: {m['architecture']['modality']}")
    if detail and m.get("top_provider"):
        lines.append(f"  Top provider: {m['top_provider']}")
    return "\n".join(lines)


# ── Tools ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_models(
    modality: str = "text",
    sort_by: str = "name",
) -> str:
    """List models available on OpenRouter.

    Args:
        modality: Filter by output type. Options: text, image, audio, embeddings, all
        sort_by: Sort by: name, created, price, context_length
    """
    models = fetch_models()

    if modality and modality != "all":
        models = [
            m for m in models
            if modality in m.get("arch_modality", ["text"])
        ]

    key_map = {
        "name": lambda m: m.get("name", "").lower(),
        "created": lambda m: m.get("created", 0),
        "price": lambda m: float(m.get("pricing", {}).get("prompt", 0)),
        "context_length": lambda m: m.get("context_length", 0),
    }
    key_fn = key_map.get(sort_by, key_map["name"])
    reverse = sort_by in ("created", "context_length")
    models = sorted(models, key=key_fn, reverse=reverse)

    header = f"# OpenRouter Models — {len(models)} results ({modality}, sorted by {sort_by})\n"
    return header + "\n\n".join(_format_model(m) for m in models[:100])


@mcp.tool()
def get_model(model_id: str) -> str:
    """Get detailed info for one model.

    Args:
        model_id: Model slug, e.g. 'anthropic/claude-sonnet-4.6'
    """
    models = fetch_models()
    for m in models:
        if m["id"] == model_id:
            return _format_model(m, detail=True)
    # Fuzzy
    matches = [m for m in models if model_id.lower() in m["id"].lower()]
    if matches:
        return _format_model(matches[0], detail=True)
    return f"Model '{model_id}' not found on OpenRouter."


@mcp.tool()
def search_models(
    query: str = "",
    provider: str = "",
    max_input_price: float = 0,
    min_context: int = 0,
    requires_tools: bool = False,
    requires_vision: bool = False,
    free_only: bool = False,
) -> str:
    """Search and filter OpenRouter models.

    Args:
        query: Free-text search in model name/id/description
        provider: Filter by provider (anthropic, google, openai, etc.)
        max_input_price: Max input price per 1M tokens, 0 = no limit
        min_context: Minimum context window size
        requires_tools: Only models supporting tool calling
        requires_vision: Only models with vision/image input
        free_only: Only free models
    """
    models = fetch_models()
    results = []

    for m in models:
        if query:
            searchable = f"{m.get('id','')} {m.get('name','')} {m.get('description','')}".lower()
            if not all(w in searchable for w in query.lower().split()):
                continue
        if provider and provider.lower() not in m.get("id", "").lower():
            continue
        if max_input_price > 0:
            if float(m.get("pricing", {}).get("prompt", 0)) * 1_000_000 > max_input_price:
                continue
        if min_context > 0 and m.get("context_length", 0) < min_context:
            continue
        if requires_tools and "tools" not in m.get("supported_parameters", []):
            continue
        if requires_vision:
            mods = m.get("arch_modality", [])
            if "image" not in mods and "image-to-text" not in mods:
                continue
        if free_only:
            p = m.get("pricing", {})
            if float(p.get("prompt", 0)) > 0 or float(p.get("completion", 0)) > 0:
                continue
        results.append(m)

    if not results:
        return "No models match your criteria."

    lines = [f"# Search Results — {len(results)} models\n"]
    for m in results[:50]:
        lines.append(_format_model(m))
    if len(results) > 50:
        lines.append(f"\n... and {len(results) - 50} more")
    return "\n\n".join(lines)


@mcp.tool()
def compare_models(model_ids: str) -> str:
    """Compare multiple models side by side.

    Args:
        model_ids: Comma-separated model IDs
    """
    models = fetch_models()
    ids = [x.strip() for x in model_ids.split(",")]
    selected = []
    for mid in ids:
        for m in models:
            if m["id"] == mid or mid.lower() in m["id"].lower():
                selected.append(m)
                break
    if not selected:
        return "No matching models found."

    names = [m["id"] for m in selected]
    max_len = max(len(n) for n in names) if names else 10

    def row(label, fn):
        vals = " | ".join(str(fn(m)).rjust(max_len) for m in selected)
        return f"| {label} | {vals} |"

    lines = ["# Model Comparison\n"]
    lines.append("| Metric | " + " | ".join(n.rjust(max_len) for n in names) + " |")
    lines.append("|--------|" + "|".join("-" * (max_len + 2) for _ in names) + "|")
    lines.append(row("Context", lambda m: m.get("context_length", "?")))
    lines.append(row("Input $/1M", lambda m: _price_str(float(m.get("pricing",{}).get("prompt",0)))))
    lines.append(row("Output $/1M", lambda m: _price_str(float(m.get("pricing",{}).get("completion",0)))))
    lines.append(row("Tools", lambda m: "✅" if "tools" in m.get("supported_parameters",[]) else "❌"))
    return "\n".join(lines)


@mcp.tool()
def refresh_cache() -> str:
    """Force refresh the model cache from OpenRouter."""
    _cache["data"] = None
    models = fetch_models(force=True)
    return f"Cache refreshed. {len(models)} models loaded."


def main():
    """Entry point for CLI."""
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
