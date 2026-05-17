"""Factory for embedding providers."""

from __future__ import annotations

import os

from .base import EmbeddingProvider
from .gemini_langchain import GoogleGeminiEmbeddingProvider
from .openrouter import OpenRouterEmbeddingProvider

GOOGLE_GEMINI_PRESETS = {"", "google", "google_gemini", "gemini", "gemini-2.5-pro"}
OPENROUTER_GEMINI_PRESETS = {"openrouter_gemini", "openrouter", "openrouter-gemini"}


def normalize_api_keys(api_keys) -> list[str]:
    if isinstance(api_keys, str):
        return [item.strip() for item in api_keys.split(",") if item.strip()]
    if isinstance(api_keys, (list, tuple)):
        return [str(item).strip() for item in api_keys if str(item).strip()]
    return []


def create_embedding_provider(llm_config: dict, workflow_config: dict) -> EmbeddingProvider:
    api_keys = normalize_api_keys((llm_config or {}).get("api"))
    if not api_keys:
        raise ValueError("At least one API key is required for embedding")

    preset = str((llm_config or {}).get("model") or "").strip().lower()
    batch_size = int(workflow_config.get("embedding_batch_size", 50))
    timeout_seconds = int(workflow_config.get("embedding_timeout_seconds", 180))
    max_retries = int(workflow_config.get("embedding_max_retries", 2))

    if preset in OPENROUTER_GEMINI_PRESETS:
        return OpenRouterEmbeddingProvider(
            api_keys=api_keys,
            model=os.getenv("OPENROUTER_GEMINI_EMBEDDING_MODEL", "google/gemini-embedding-2-preview"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    if preset not in GOOGLE_GEMINI_PRESETS:
        # Keep the legacy behavior permissive: unknown old values still use Google.
        preset = "google_gemini"

    return GoogleGeminiEmbeddingProvider(
        api_keys=api_keys,
        model=os.getenv("GOOGLE_GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
        batch_size=batch_size,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
