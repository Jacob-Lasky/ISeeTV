from __future__ import annotations

from typing import Any, Optional

import httpx

from common.constants import MEILI_ENABLED, MEILI_HOST, MEILI_MASTER_KEY
from common.log_utils import get_logger

logger = get_logger(__name__)


class MeiliClient:
    """Lightweight Meilisearch client wrapper using httpx.

    Feature-flag aware. Avoids adding an SDK dependency for now.
    """

    def __init__(self, host: str, api_key: str | None = None) -> None:
        self.host = host.rstrip("/")
        self.api_key = api_key or ""

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def health(self) -> dict[str, Any]:
        url = f"{self.host}/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def version(self) -> dict[str, Any]:
        url = f"{self.host}/version"
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def search(self, index: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform a search on an index.

        payload supports Meili's search params, e.g.:
        {
          "q": "query",
          "offset": 0,
          "limit": 20,
          "filter": "source = 'X'",
          "sort": ["field:asc"],
          "facets": ["field1", "field2"]
        }
        """
        url = f"{self.host}/indexes/{index}/search"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            return r.json()

    async def set_settings(self, index: str, settings: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.host}/indexes/{index}/settings"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.patch(url, headers=self._headers(), json=settings)
            r.raise_for_status()
            return r.json()

    async def delete_documents(self, index: str, ids: list[str]) -> dict[str, Any]:
        url = f"{self.host}/indexes/{index}/documents/delete-batch"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=self._headers(), json={"ids": ids})
            r.raise_for_status()
            return r.json()

    async def upsert_documents(self, index: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
        url = f"{self.host}/indexes/{index}/documents"
        async with httpx.AsyncClient(timeout=None) as client:  # can be longer for batches
            r = await client.put(url, headers=self._headers(), json=docs)
            r.raise_for_status()
            return r.json()

    async def delete_all_documents(self, index: str) -> dict[str, Any]:
        """Delete all documents from an index.

        This is useful for full rebuilds. Meilisearch returns a task object.
        """
        url = f"{self.host}/indexes/{index}/documents"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.delete(url, headers=self._headers())
            r.raise_for_status()
            # Some versions may return an empty body for 204; guard accordingly
            return r.json() if r.text else {"status": "enqueued"}


def meili_enabled() -> bool:
    return MEILI_ENABLED


def get_meili_client() -> Optional[MeiliClient]:
    if not MEILI_ENABLED:
        return None
    client = MeiliClient(MEILI_HOST, MEILI_MASTER_KEY)
    logger.debug("Initialized MeiliClient: host=%s enabled=%s", MEILI_HOST, MEILI_ENABLED)
    return client
