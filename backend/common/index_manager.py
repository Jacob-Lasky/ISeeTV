"""Meilisearch index management for ISeeTV.

This module handles creation, configuration, and synchronization of Meilisearch indexes
for the ISeeTV application. It provides atomic operations for index management and
modular document synchronization.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from common.constants import MEILI_ENABLED
from common.db import SessionLocal
from common.log_utils import get_logger
from common.search_client import get_meili_client
from common.task_manager import IndexingTaskManager

logger = get_logger(__name__)


class IndexConfig:
    """Configuration for a Meilisearch index."""
    
    def __init__(
        self,
        name: str,
        primary_key: str,
        searchable_attributes: List[str],
        filterable_attributes: List[str],
        sortable_attributes: List[str],
        table_name: str,
        displayed_attributes: Optional[List[str]] = None,
    ):
        self.name = name
        self.primary_key = primary_key
        self.searchable_attributes = searchable_attributes
        self.filterable_attributes = filterable_attributes
        self.sortable_attributes = sortable_attributes
        self.table_name = table_name
        self.displayed_attributes = displayed_attributes or ["*"]


class IndexManager:
    """Manages Meilisearch indexes for ISeeTV tables."""
    
    # Index configurations for each supported table
    INDEX_CONFIGS = {
        "m3u_channels": IndexConfig(
            name="m3u_channels",
            primary_key="id",
            searchable_attributes=[
                "name",
                "tvg_id", 
                "group",
                "stream_url",
                "logo_url",
                "source",
                "_trace"
            ],
            filterable_attributes=[
                "source",
                "group", 
                "stream_mode",
                "filter_reasons",
                "tvg_id",
                "name",
                "created_at",
                "updated_at"
            ],
            sortable_attributes=[
                "id",
                "name",
                "tvg_id",
                "group",
                "stream_mode", 
                "created_at",
                "updated_at"
            ],
            table_name="m3u_channels"
        ),
        "epg_channels": IndexConfig(
            name="epg_channels", 
            primary_key="id",
            searchable_attributes=[
                "channel_id",
                "display_name",
                "icon_url",
                "source",
                "_trace"
            ],
            filterable_attributes=[
                "source",
                "filter_reasons",
                "channel_id",
                "display_name",
                "created_at",
                "updated_at"
            ],
            sortable_attributes=[
                "id",
                "channel_id",
                "display_name",
                "created_at",
                "updated_at"
            ],
            table_name="epg_channels"
        ),
        "programs": IndexConfig(
            name="programs",
            primary_key="id", 
            searchable_attributes=[
                "program_id",
                "channel_id",
                "title",
                "description",
                "source",
                "_trace"
            ],
            filterable_attributes=[
                "source",
                "channel_id",
                "filter_reasons",
                "program_id",
                "title",
                "start_time",
                "end_time",
                "created_at",
                "updated_at"
            ],
            sortable_attributes=[
                "id",
                "program_id",
                "channel_id",
                "title",
                "start_time",
                "end_time",
                "created_at", 
                "updated_at"
            ],
            table_name="programs"
        )
    }
    
    def __init__(self):
        self.client = get_meili_client()
    
    async def ensure_index_exists(self, index_name: str) -> bool:
        """Ensure a Meilisearch index exists, creating it if necessary.
        
        Returns:
            True if index exists or was created successfully, False otherwise.
        """
        if not MEILI_ENABLED or not self.client:
            logger.warning("Meilisearch is disabled or client not available")
            return False
            
        config = self.INDEX_CONFIGS.get(index_name)
        if not config:
            logger.error("No configuration found for index: %s", index_name)
            return False
            
        try:
            # Try to get index info (will raise if doesn't exist)
            await self._get_index_info(index_name)
            logger.debug("Index %s already exists", index_name)
            return True
        except Exception:
            # Index doesn't exist, create it
            logger.info("Creating index: %s", index_name)
            return await self._create_index(config)
    
    async def _get_index_info(self, index_name: str) -> Dict[str, Any]:
        """Get information about an index."""
        url = f"{self.client.host}/indexes/{index_name}"
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=self.client._headers())
            response.raise_for_status()
            return response.json()
    
    async def _create_index(self, config: IndexConfig) -> bool:
        """Create a new Meilisearch index with proper configuration."""
        try:
            # Create the index
            url = f"{self.client.host}/indexes"
            payload = {
                "uid": config.name,
                "primaryKey": config.primary_key
            }
            
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url, 
                    headers=self.client._headers(), 
                    json=payload
                )
                response.raise_for_status()
                task_info = response.json()
                logger.info("Index creation task: %s", task_info)
            
            # Wait a moment for index creation to complete
            await asyncio.sleep(1)
            
            # Configure index settings
            settings = {
                "searchableAttributes": config.searchable_attributes,
                "filterableAttributes": config.filterable_attributes, 
                "sortableAttributes": config.sortable_attributes,
                "displayedAttributes": config.displayed_attributes
            }
            
            await self.client.set_settings(config.name, settings)
            logger.info("Configured settings for index: %s", config.name)
            
            return True
            
        except Exception as e:
            logger.error("Failed to create index %s: %s", config.name, e)
            return False
    
    async def sync_table_to_index(
        self, 
        index_name: str, 
        source_name: Optional[str] = None,
        batch_size: int = 5000
    ) -> bool:
        """Synchronize database table data to Meilisearch index.
        
        Args:
            index_name: Name of the index to sync
            source_name: Optional source filter for data
            batch_size: Number of documents to process per batch
            
        Returns:
            True if sync completed successfully, False otherwise.
        """
        if not MEILI_ENABLED or not self.client:
            logger.warning("Meilisearch is disabled or client not available")
            return False
            
        config = self.INDEX_CONFIGS.get(index_name)
        if not config:
            logger.error("No configuration found for index: %s", index_name)
            return False
        
        # Ensure index exists
        if not await self.ensure_index_exists(index_name):
            logger.error("Failed to ensure index exists: %s", index_name)
            return False
        
        task_id = f"sync_{index_name}_{source_name or 'all'}"
        
        try:
            with SessionLocal() as db:
                # Get total count for progress tracking
                count_query = f"SELECT COUNT(*) FROM {config.table_name}"
                if source_name:
                    count_query += " WHERE source = :source_name"
                
                result = db.execute(
                    text(count_query),
                    {"source_name": source_name} if source_name else {}
                )
                total_count = result.scalar()
                
                if total_count == 0:
                    logger.info("No data to sync for index: %s", index_name)
                    return True
                
                # Create indexing task
                IndexingTaskManager.create_indexing_task(
                    task_id=task_id,
                    index_name=index_name,
                    source_name=source_name,
                    total_items=total_count
                )
                
                # Process data in batches
                offset = 0
                processed = 0
                
                while offset < total_count:
                    # Fetch batch of data
                    data_query = f"SELECT * FROM {config.table_name}"
                    if source_name:
                        data_query += " WHERE source = :source_name"
                    data_query += f" ORDER BY id LIMIT {batch_size} OFFSET {offset}"
                    
                    result = db.execute(
                        text(data_query),
                        {"source_name": source_name} if source_name else {}
                    )
                    
                    rows = result.fetchall()
                    if not rows:
                        break
                    
                    # Convert rows to documents
                    documents = []
                    for row in rows:
                        doc = dict(row._mapping)
                        # Convert datetime objects to ISO strings
                        for key, value in doc.items():
                            if hasattr(value, 'isoformat'):
                                doc[key] = value.isoformat()
                        documents.append(doc)
                    
                    # Upsert documents to Meilisearch
                    await self.client.upsert_documents(index_name, documents)
                    
                    processed += len(documents)
                    offset += batch_size
                    
                    # Update progress
                    IndexingTaskManager.update_item_progress(
                        task_id=task_id,
                        processed_items=processed
                    )
                    
                    # Only log every 10th batch to reduce noise
                    if processed % (batch_size * 10) == 0 or processed == total_count:
                        logger.info(
                            "Synced %d/%d documents for index %s", 
                            processed, total_count, index_name
                        )
                
                # Mark task as completed
                IndexingTaskManager.complete_task(task_id)
                logger.info(
                    "Successfully synced %d documents to index: %s", 
                    processed, index_name
                )
                return True
                
        except Exception as e:
            logger.error("Failed to sync table to index %s: %s", index_name, e)
            IndexingTaskManager.fail_task(task_id, str(e))
            return False
    
    async def rebuild_index(self, index_name: str, source_name: Optional[str] = None) -> bool:
        """Completely rebuild a Meilisearch index.
        
        This clears all existing documents and re-syncs from the database.
        """
        if not MEILI_ENABLED or not self.client:
            logger.warning("Meilisearch is disabled or client not available")
            return False
            
        logger.info("Rebuilding index: %s", index_name)
        
        try:
            # Ensure index exists
            if not await self.ensure_index_exists(index_name):
                logger.error("Failed to ensure index exists: %s", index_name)
                return False
            
            # Clear all documents
            await self.client.delete_all_documents(index_name)
            logger.info("Cleared all documents from index: %s", index_name)
            
            # Wait for deletion to complete
            await asyncio.sleep(2)
            
            # Re-sync data
            return await self.sync_table_to_index(index_name, source_name)
            
        except Exception as e:
            logger.error("Failed to rebuild index %s: %s", index_name, e)
            return False
    
    async def initialize_all_indexes(self) -> Dict[str, bool]:
        """Initialize all configured indexes.
        
        Returns:
            Dictionary mapping index names to success status.
        """
        if not MEILI_ENABLED or not self.client:
            logger.warning("Meilisearch is disabled or client not available")
            return {}
        
        results = {}
        
        for index_name in self.INDEX_CONFIGS.keys():
            logger.info("Initializing index: %s", index_name)
            success = await self.ensure_index_exists(index_name)
            results[index_name] = success
            
            if success:
                logger.info("Successfully initialized index: %s", index_name)
            else:
                logger.error("Failed to initialize index: %s", index_name)
        
        return results
    
    async def sync_all_indexes(self) -> Dict[str, bool]:
        """Sync all configured indexes with their corresponding database tables.
        
        Returns:
            Dictionary mapping index names to sync success status.
        """
        if not MEILI_ENABLED or not self.client:
            logger.warning("Meilisearch is disabled or client not available")
            return {}
        
        results = {}
        
        for index_name in self.INDEX_CONFIGS.keys():
            logger.info("Syncing index: %s", index_name)
            success = await self.sync_table_to_index(index_name)
            results[index_name] = success
            
            if success:
                logger.info("Successfully synced index: %s", index_name)
            else:
                logger.error("Failed to sync index: %s", index_name)
        
        return results


# Singleton instance
index_manager = IndexManager()


async def ensure_index_exists(index_name: str) -> bool:
    """Convenience function to ensure an index exists."""
    return await index_manager.ensure_index_exists(index_name)


async def sync_table_to_index(
    index_name: str, 
    source_name: Optional[str] = None
) -> bool:
    """Convenience function to sync a table to its index."""
    return await index_manager.sync_table_to_index(index_name, source_name)


async def initialize_all_indexes() -> Dict[str, bool]:
    """Convenience function to initialize all indexes."""
    return await index_manager.initialize_all_indexes()


async def sync_all_indexes() -> Dict[str, bool]:
    """Convenience function to sync all indexes."""
    return await index_manager.sync_all_indexes()
