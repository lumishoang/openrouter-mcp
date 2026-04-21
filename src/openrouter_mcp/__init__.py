"""OpenRouter MCP Server — Query 300+ AI models with pricing and capabilities."""

__version__ = "1.0.0"

from .server import main, fetch_models, list_models, get_model, search_models, compare_models, refresh_cache

__all__ = ["main", "fetch_models", "list_models", "get_model", "search_models", "compare_models", "refresh_cache"]
