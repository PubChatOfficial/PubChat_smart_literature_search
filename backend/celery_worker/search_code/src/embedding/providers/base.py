"""Embedding provider interface and shared retry/key helpers."""

from __future__ import annotations

import random
import threading
import time
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed query text with retrieval-query semantics."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document texts with retrieval-document semantics."""


class RotatingEmbeddingKeys:
    def __init__(self, keys: list[str]):
        if not keys:
            raise ValueError("At least one embedding API key must be provided")
        self._keys = keys
        self._index = random.randrange(len(keys))
        self._lock = threading.Lock()

    def next_key(self) -> str:
        with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key


def with_retries(operation, max_retries: int, retry_delay: float = 1.0):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as error:
            last_error = error
            if attempt >= max_retries:
                break
            wait_seconds = min(retry_delay * (2 ** attempt), 30.0)
            time.sleep(wait_seconds)
    raise last_error
