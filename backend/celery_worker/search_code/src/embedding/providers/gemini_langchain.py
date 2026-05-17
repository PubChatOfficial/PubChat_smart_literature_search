"""Google Gemini embedding provider through the native Gemini REST API."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import EmbeddingProvider, RotatingEmbeddingKeys, with_retries


class GoogleGeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_keys: list[str],
        model: str = "models/gemini-embedding-2",
        batch_size: int = 50,
        timeout_seconds: int = 180,
        max_retries: int = 2,
    ):
        self.keys = RotatingEmbeddingKeys(api_keys)
        self.model = model if model.startswith("models/") else f"models/{model}"
        self.batch_size = min(batch_size, 100)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _client(self, key: str):
        return key

    def embed_query(self, text: str) -> list[float]:
        def operation():
            return self._post_embed_content(text, task_type="RETRIEVAL_QUERY")

        return with_retries(operation, self.max_retries)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def operation():
            vectors: list[list[float]] = []
            for start in range(0, len(texts), self.batch_size):
                vectors.extend(
                    self._post_batch_embed_contents(
                        texts[start : start + self.batch_size],
                        task_type="RETRIEVAL_DOCUMENT",
                    )
                )
            return vectors

        return with_retries(operation, self.max_retries)

    def _post_embed_content(self, text: str, task_type: str) -> list[float]:
        payload = {
            "model": self.model,
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }
        data = self._post(f"{self.model}:embedContent", payload)
        values = data.get("embedding", {}).get("values")
        if not values:
            raise RuntimeError(f"Missing Gemini embedding values: {str(data)[:1000]}")
        return [float(value) for value in values]

    def _post_batch_embed_contents(self, texts: list[str], task_type: str) -> list[list[float]]:
        payload = {
            "requests": [
                {
                    "model": self.model,
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                }
                for text in texts
            ]
        }
        data = self._post(f"{self.model}:batchEmbedContents", payload)
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise RuntimeError(f"Expected {len(texts)} Gemini embeddings, got {0 if not isinstance(embeddings, list) else len(embeddings)}")

        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = embedding.get("values") if isinstance(embedding, dict) else None
            if not values:
                raise RuntimeError(f"Missing Gemini batch embedding values: {str(data)[:1000]}")
            vectors.append([float(value) for value in values])
        return vectors

    def _post(self, method_path: str, payload: dict) -> dict:
        api_key = self.keys.next_key()
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/{method_path}?key={api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Gemini embedding HTTP {error.code}: {body}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"Gemini embedding request failed: {error}") from error
