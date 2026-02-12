"""
Database utilities for testing.

This module provides utilities for setting up and managing test databases,
including fixtures for both PostgreSQL and SQLite testing scenarios.
"""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator
from unittest.mock import patch

import pytest
import redis.asyncio as aioredis
from elasticsearch import AsyncElasticsearch
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.mandi_platform.config import Settings
from src.mandi_platform.models.base import Base


class TestDatabaseManager:
    """Manages test database lifecycle and operations."""
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///:memory:"):
        self.database_url = database_url
        self.engine = None
        self.session_maker = None
    
    async def setup(self):
        """Set up the test database."""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
        )
        
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.session_maker = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def teardown(self):
        """Clean up the test database."""
        if self.engine:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await self.engine.dispose()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session for testing."""
        if not self.session_maker:
            await self.setup()
        
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def reset_database(self):
        """Reset the database to a clean state."""
        if self.engine:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)


class TestRedisManager:
    """Manages test Redis instance and operations."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/15"):
        self.redis_url = redis_url
        self.redis = None
    
    async def setup(self):
        """Set up the test Redis connection."""
        self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
        
        # Test connection
        try:
            await self.redis.ping()
        except Exception as e:
            # If Redis is not available, use a mock
            from unittest.mock import AsyncMock
            self.redis = AsyncMock(spec=aioredis.Redis)
            self.redis.ping.return_value = True
    
    async def teardown(self):
        """Clean up the test Redis connection."""
        if self.redis and hasattr(self.redis, 'close'):
            await self.redis.flushdb()  # Clear test data
            await self.redis.close()
    
    async def clear_all_data(self):
        """Clear all data from the test Redis database."""
        if self.redis and hasattr(self.redis, 'flushdb'):
            await self.redis.flushdb()


class TestElasticsearchManager:
    """Manages test Elasticsearch instance and operations."""
    
    def __init__(self, es_url: str = "http://localhost:9200"):
        self.es_url = es_url
        self.es = None
        self.test_indices = []
    
    async def setup(self):
        """Set up the test Elasticsearch connection."""
        self.es = AsyncElasticsearch([self.es_url])
        
        # Test connection
        try:
            await self.es.ping()
        except Exception:
            # If Elasticsearch is not available, use a mock
            from unittest.mock import AsyncMock
            self.es = AsyncMock(spec=AsyncElasticsearch)
            self.es.ping.return_value = True
    
    async def teardown(self):
        """Clean up the test Elasticsearch connection."""
        if self.es and hasattr(self.es, 'close'):
            # Delete test indices
            for index in self.test_indices:
                try:
                    await self.es.indices.delete(index=index, ignore=[404])
                except Exception:
                    pass
            
            await self.es.close()
    
    async def create_test_index(self, index_name: str, mapping: dict = None):
        """Create a test index."""
        if hasattr(self.es, 'indices'):
            await self.es.indices.create(
                index=index_name,
                body={"mappings": mapping} if mapping else {},
                ignore=[400]  # Ignore if index already exists
            )
            self.test_indices.append(index_name)
    
    async def clear_test_indices(self):
        """Clear all test indices."""
        for index in self.test_indices:
            try:
                if hasattr(self.es, 'indices'):
                    await self.es.indices.delete(index=index, ignore=[404])
            except Exception:
                pass
        self.test_indices.clear()


class IntegrationTestEnvironment:
    """Manages the complete test environment for integration tests."""
    
    def __init__(self):
        self.db_manager = TestDatabaseManager()
        self.redis_manager = TestRedisManager()
        self.es_manager = TestElasticsearchManager()
    
    async def setup(self):
        """Set up the complete test environment."""
        await self.db_manager.setup()
        await self.redis_manager.setup()
        await self.es_manager.setup()
    
    async def teardown(self):
        """Clean up the complete test environment."""
        await self.db_manager.teardown()
        await self.redis_manager.teardown()
        await self.es_manager.teardown()
    
    async def reset_all(self):
        """Reset all components to clean state."""
        await self.db_manager.reset_database()
        await self.redis_manager.clear_all_data()
        await self.es_manager.clear_test_indices()
    
    def get_test_settings(self) -> Settings:
        """Get test settings for the environment."""
        return Settings(
            database_url=self.db_manager.database_url,
            redis_url=self.redis_manager.redis_url,
            elasticsearch_url=self.es_manager.es_url,
            secret_key="test-secret-key-for-testing-only",
            algorithm="HS256",
            access_token_expire_minutes=30,
            environment="test",
            debug=True,
        )


# Utility functions for test data management

async def populate_test_database(session: AsyncSession, data_fixtures: dict):
    """Populate test database with fixture data."""
    # This would be implemented based on the actual models
    # For now, it's a placeholder
    pass


async def create_test_user(session: AsyncSession, user_data: dict):
    """Create a test user in the database."""
    # This would be implemented based on the actual User model
    # For now, it's a placeholder
    pass


async def create_test_vendor(session: AsyncSession, vendor_data: dict):
    """Create a test vendor in the database."""
    # This would be implemented based on the actual Vendor model
    # For now, it's a placeholder
    pass


async def create_test_product(session: AsyncSession, product_data: dict):
    """Create a test product in the database."""
    # This would be implemented based on the actual Product model
    # For now, it's a placeholder
    pass


# Context managers for test isolation

@asynccontextmanager
async def get_test_db_session():
    """Get a test database session."""
    db_manager = TestDatabaseManager()
    await db_manager.setup()
    try:
        async with db_manager.get_session() as session:
            yield session
    finally:
        await db_manager.teardown()


@asynccontextmanager
async def isolated_test_environment():
    """Context manager for isolated test environment."""
    env = IntegrationTestEnvironment()
    await env.setup()
    try:
        yield env
    finally:
        await env.teardown()


@asynccontextmanager
async def test_transaction(session: AsyncSession):
    """Context manager for test transaction that rolls back."""
    transaction = await session.begin()
    try:
        yield session
    finally:
        await transaction.rollback()


# Pytest fixtures that can be imported

@pytest.fixture(scope="session")
async def test_environment():
    """Session-scoped test environment."""
    env = IntegrationTestEnvironment()
    await env.setup()
    yield env
    await env.teardown()


@pytest.fixture
async def clean_test_environment(test_environment):
    """Function-scoped clean test environment."""
    await test_environment.reset_all()
    yield test_environment