"""
Elasticsearch client configuration and management.

This module provides Elasticsearch connection management for product search
and analytics functionality.
"""

from typing import Any, Dict, List, Optional, Union
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError

from .config import settings


class ElasticsearchManager:
    """Manages Elasticsearch connections and operations."""
    
    def __init__(self, elasticsearch_url: str, index_prefix: str):
        """Initialize Elasticsearch manager."""
        self.elasticsearch_url = elasticsearch_url
        self.index_prefix = index_prefix
        self.client: Optional[AsyncElasticsearch] = None
    
    async def connect(self) -> AsyncElasticsearch:
        """Connect to Elasticsearch and return client."""
        if self.client is None:
            self.client = AsyncElasticsearch(
                [self.elasticsearch_url],
                verify_certs=False,  # Set to True in production with proper certs
                ssl_show_warn=False,
            )
        return self.client
    
    async def disconnect(self):
        """Disconnect from Elasticsearch."""
        if self.client:
            await self.client.close()
            self.client = None
    
    def get_index_name(self, index_type: str) -> str:
        """Get full index name with prefix."""
        return f"{self.index_prefix}_{index_type}"
    
    async def create_index(
        self,
        index_type: str,
        mapping: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create an index with mapping and settings."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        body = {"mappings": mapping}
        if settings:
            body["settings"] = settings
        
        try:
            await client.indices.create(index=index_name, body=body)
            return True
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                return True  # Index already exists
            raise
    
    async def delete_index(self, index_type: str) -> bool:
        """Delete an index."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        try:
            await client.indices.delete(index=index_name)
            return True
        except NotFoundError:
            return False  # Index doesn't exist
    
    async def index_exists(self, index_type: str) -> bool:
        """Check if an index exists."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        return await client.indices.exists(index=index_name)
    
    async def index_document(
        self,
        index_type: str,
        document_id: str,
        document: Dict[str, Any],
        refresh: bool = False,
    ) -> bool:
        """Index a document."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        try:
            await client.index(
                index=index_name,
                id=document_id,
                body=document,
                refresh=refresh,
            )
            return True
        except Exception:
            return False
    
    async def get_document(
        self, index_type: str, document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        try:
            response = await client.get(index=index_name, id=document_id)
            return response["_source"]
        except NotFoundError:
            return None
    
    async def update_document(
        self,
        index_type: str,
        document_id: str,
        document: Dict[str, Any],
        refresh: bool = False,
    ) -> bool:
        """Update a document."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        try:
            await client.update(
                index=index_name,
                id=document_id,
                body={"doc": document},
                refresh=refresh,
            )
            return True
        except Exception:
            return False
    
    async def delete_document(
        self, index_type: str, document_id: str, refresh: bool = False
    ) -> bool:
        """Delete a document."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        try:
            await client.delete(
                index=index_name, id=document_id, refresh=refresh
            )
            return True
        except NotFoundError:
            return False
    
    async def search(
        self,
        index_type: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Search documents."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        body = {
            "query": query,
            "size": size,
            "from": from_,
        }
        
        if sort:
            body["sort"] = sort
        
        try:
            response = await client.search(index=index_name, body=body)
            return response
        except Exception as e:
            return {"hits": {"hits": [], "total": {"value": 0}}, "error": str(e)}
    
    async def bulk_index(
        self,
        index_type: str,
        documents: List[Dict[str, Any]],
        refresh: bool = False,
    ) -> bool:
        """Bulk index documents."""
        client = await self.connect()
        index_name = self.get_index_name(index_type)
        
        body = []
        for doc in documents:
            doc_id = doc.get("id") or doc.get("_id")
            body.append({"index": {"_index": index_name, "_id": doc_id}})
            body.append(doc)
        
        try:
            await client.bulk(body=body, refresh=refresh)
            return True
        except Exception:
            return False
    
    async def ping(self) -> bool:
        """Ping Elasticsearch to check connection."""
        try:
            client = await self.connect()
            return await client.ping()
        except Exception:
            return False


# Global Elasticsearch manager instance
_es_manager: Optional[ElasticsearchManager] = None


def get_elasticsearch_manager() -> ElasticsearchManager:
    """Get or create the global Elasticsearch manager."""
    global _es_manager
    
    if _es_manager is None:
        _es_manager = ElasticsearchManager(
            settings.elasticsearch_url,
            settings.elasticsearch_index_prefix,
        )
    
    return _es_manager


async def get_elasticsearch_client() -> AsyncElasticsearch:
    """Dependency for getting Elasticsearch client in FastAPI."""
    es_manager = get_elasticsearch_manager()
    return await es_manager.connect()


async def close_elasticsearch():
    """Close Elasticsearch connections."""
    global _es_manager
    if _es_manager:
        await _es_manager.disconnect()
        _es_manager = None