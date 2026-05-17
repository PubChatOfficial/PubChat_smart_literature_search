"""Embedding prefilter components for literature screening."""

from .providers.factory import create_embedding_provider
from .streaming_pipeline import StreamingEmbeddingScreeningPipeline

__all__ = [
    "create_embedding_provider",
    "StreamingEmbeddingScreeningPipeline",
]
