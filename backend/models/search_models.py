"""Search models for Meilisearch-backed endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class SearchResponse(BaseModel):
    """Generic Meilisearch search response wrapper.

    Uses extra="allow" to pass through additional fields provided by Meilisearch
    without forcing a strict schema, while still documenting the common ones.
    """

    model_config = ConfigDict(extra="allow")

    # Common fields
    hits: list[dict[str, Any]] = []
    query: str | None = None
    offset: int | None = 0
    limit: int | None = 20
    processingTimeMs: int | None = None

    # Totals (Meilisearch v1 uses estimatedTotalHits; some setups may expose totalHits)
    estimatedTotalHits: int | None = None
    totalHits: int | None = None

    # Faceting (depending on Meilisearch version/config)
    facetDistribution: dict[str, Any] | None = None
    facetsDistribution: dict[str, Any] | None = None
    facetStats: dict[str, Any] | None = None

    # Index metadata (optional in some responses)
    indexUid: str | None = None
