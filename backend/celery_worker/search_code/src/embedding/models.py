"""Data models for embedding prefiltering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class EmbeddingDecision:
    article: dict
    pmid: str
    text: str
    similarity: Optional[float]
    passed: bool
    error: str = ""


@dataclass
class EmbeddingBatchResult:
    decisions: list[EmbeddingDecision]
    elapsed_seconds: float
    error: str = ""
