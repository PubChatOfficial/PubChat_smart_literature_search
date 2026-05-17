"""Build embedding document text from article metadata."""

from __future__ import annotations

from typing import Any


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(item for item in (clean_text(part) for part in value) if item)
    return " ".join(str(value).split())


class ArticleTextBuilder:
    """Construct dense document text from title, abstract, and keywords."""

    @staticmethod
    def build(article: dict) -> str:
        title = clean_text(article.get("title") or article.get("article_title"))
        abstract = clean_text(article.get("abstract"))
        keywords = clean_text(article.get("keywords"))
        parts = [
            f"Title: {title}" if title else "",
            f"Abstract: {abstract}" if abstract else "",
            f"Keywords: {keywords}" if keywords else "",
        ]
        return "\n".join(part for part in parts if part).strip()
