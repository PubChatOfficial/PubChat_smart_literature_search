"""OpenRouter embedding provider."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import EmbeddingProvider, RotatingEmbeddingKeys, with_retries


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_keys: list[str],
        model: str = "google/gemini-embedding-2-preview",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 180,
        max_retries: int = 2,
    ):
        self.keys = RotatingEmbeddingKeys(api_keys)
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed([text], input_type="search_query")
        return vectors[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, input_type="search_document")

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        def operation():
            return self._post_embeddings(texts, input_type)

        return with_retries(operation, self.max_retries)

    def _post_embeddings(self, texts: list[str], input_type: str) -> list[list[float]]:
        payload = {
            "model": self.model,
            "input": texts,
            "input_type": input_type,
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/embeddings",
            data=data,
            headers={
                "Authorization": f"Bearer {self.keys.next_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"OpenRouter embedding HTTP {error.code}: {body}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"OpenRouter embedding request failed: {error}") from error

        data_rows = body.get("data")
        if not isinstance(data_rows, list) or len(data_rows) != len(texts):
            raise RuntimeError(f"Unexpected OpenRouter embedding response: {str(body)[:1000]}")

        vectors: list[list[float]] = []
        for row in sorted(data_rows, key=lambda item: item.get("index", 0)):
            vector = row.get("embedding") if isinstance(row, dict) else None
            if not vector:
                raise RuntimeError(f"Missing embedding vector in OpenRouter response: {str(body)[:1000]}")
            vectors.append([float(value) for value in vector])
        return vectors
