"""Where a generated product field came from.

The labels deliberately keep rule-based output separate from real AI output so
the storefront never presents an offline fallback as an AI result.
"""
from django.db import models


class ContentSource(models.TextChoices):
    OWNER = "owner", "Owner-supplied"
    SEED = "seed", "Curated demo"
    OLLAMA = "ollama", "AI · Ollama"
    HUGGINGFACE = "huggingface", "AI · Hugging Face"
    FALLBACK = "fallback", "Offline fallback (not AI)"


AI_SOURCES = frozenset({ContentSource.OLLAMA, ContentSource.HUGGINGFACE})
FALLBACK_SOURCE = ContentSource.FALLBACK


def is_ai_source(source):
    return source in AI_SOURCES


def source_label(source):
    try:
        return ContentSource(source).label
    except (TypeError, ValueError):
        return "Unknown source"
