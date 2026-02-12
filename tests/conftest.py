"""
Pytest configuration and fixtures for the Multilingual Mandi Platform.

This module provides shared fixtures and configuration for both unit tests
and property-based tests using Hypothesis.
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

try:
    from elasticsearch import AsyncElasticsearch
except ImportError:
    AsyncElasticsearch = None

try:
    from fastapi.testclient import TestClient
    from httpx import AsyncClient
except ImportError:
    TestClient = None
    AsyncClient = None

try:
    from sqlalchemy import create_engine, event
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
except ImportError:
    pass

# Import application components if available
try:
    from mandi_platform.config import Settings, get_settings
    from mandi_platform.database import Base, get_db_session
    from mandi_platform.main import app
    from mandi_platform.redis_client import get_redis
    from mandi_platform.elasticsearch_client import get_elasticsearch
    from mandi_platform.models.user import User, Vendor
    from mandi_platform.models.enums import (
        LanguageCode,
        TechLiteracyLevel,
        VerificationStatus,
        BusinessType,
        MarketReputation
    )
    from mandi_platform.auth.jwt import create_access_token, create_user_token
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Only create app-dependent fixtures if the app is available
if APP_AVAILABLE:
    @pytest.fixture
    def test_settings():
        """Create test settings with overrides for testing environment."""
        return Settings(
            database_url=TEST_DATABASE_URL,
            redis_url="redis://localhost:6379/1",  # Use test database
            elasticsearch_url="http://localhost:9200",
            secret_key="test-secret-key-for-testing-only",
            algorithm="HS256",
            access_token_expire_minutes=30,
            environment="test",
            debug=True,
        )
    
    @pytest.fixture
    async def async_client():
        """Create async HTTP client for testing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
else:
    @pytest.fixture
    def test_settings():
        """Mock test settings when app is not available."""
        return MagicMock()


@pytest.fixture
async def mock_redis() -> AsyncMock:
    """Create mock Redis client for testing."""
    if aioredis:
        mock_redis = AsyncMock(spec=aioredis.Redis)
    else:
        mock_redis = AsyncMock()
    
    # Mock common Redis operations
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    mock_redis.ping.return_value = True
    
    return mock_redis


@pytest.fixture
async def mock_elasticsearch() -> AsyncMock:
    """Create mock Elasticsearch client for testing."""
    if AsyncElasticsearch:
        mock_es = AsyncMock(spec=AsyncElasticsearch)
    else:
        mock_es = AsyncMock()
    
    # Mock common Elasticsearch operations
    mock_es.ping.return_value = True
    mock_es.search.return_value = {
        "hits": {
            "total": {"value": 0},
            "hits": []
        }
    }
    mock_es.index.return_value = {"_id": "test-id", "result": "created"}
    mock_es.delete.return_value = {"result": "deleted"}
    mock_es.update.return_value = {"result": "updated"}
    
    return mock_es


# Property-based testing fixtures and utilities

@pytest.fixture
def hypothesis_settings():
    """Configure Hypothesis settings for property-based tests."""
    from hypothesis import settings, Verbosity
    
    return settings(
        max_examples=100,  # Minimum 100 iterations as specified
        verbosity=Verbosity.verbose,
        deadline=None,  # Disable deadline for complex tests
        suppress_health_check=[],
    )


# Test data factories and generators will be added here as needed
# for specific property-based tests

# Utility functions for test setup

def create_test_user_data():
    """Create sample user data for testing."""
    return {
        "phone_number": "+919876543210",
        "preferred_language": "hi",
        "location": {
            "state": "Delhi",
            "city": "New Delhi",
            "pincode": "110001"
        },
        "tech_literacy_level": "medium",
    }


def create_test_vendor_data():
    """Create sample vendor data for testing."""
    return {
        **create_test_user_data(),
        "business_name": "Test Vendor Business",
        "business_type": "retail",
        "specializations": ["vegetables", "fruits"],
    }


def create_test_product_data():
    """Create sample product data for testing."""
    return {
        "name": {
            "en": "Fresh Tomatoes",
            "hi": "ताज़े टमाटर",
            "ta": "புதிய தக்காளி"
        },
        "category": "vegetables",
        "description": {
            "en": "Fresh red tomatoes from local farms",
            "hi": "स्थानीय खेतों से ताज़े लाल टमाटर",
            "ta": "உள்ளூர் பண்ணைகளில் இருந்து புதிய சிவப்பு தக்காளி"
        },
        "base_price": 40.00,
        "unit": "kg",
        "quality_grade": "premium",
        "availability": "in_stock",
    }


# Markers for different test types
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.property = pytest.mark.property
pytest.mark.slow = pytest.mark.slow


# Authentication fixtures (only available when app is available)
if APP_AVAILABLE:
    from uuid import uuid4
    from decimal import Decimal
    
    @pytest.fixture
    def test_user() -> User:
        """Create a test user."""
        return User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )

    @pytest.fixture
    def test_vendor() -> Vendor:
        """Create a test vendor."""
        return Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.DOCUMENT_VERIFIED,
            user_type="vendor",
            business_name="Test Vendor Business",
            business_type=BusinessType.RETAILER,
            rating=Decimal('4.2'),
            total_transactions=25,
            market_reputation=MarketReputation.DEVELOPING,
            is_verified_business=True
        )

    @pytest.fixture
    def auth_headers(test_user: User) -> dict:
        """Create authentication headers for test user."""
        token_data = create_user_token(test_user)
        access_token = create_access_token(token_data)
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.fixture
    def vendor_auth_headers(test_vendor: Vendor) -> dict:
        """Create authentication headers for test vendor."""
        token_data = create_user_token(test_vendor)
        access_token = create_access_token(token_data)
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.fixture
    def unverified_user() -> User:
        """Create an unverified test user."""
        return User(
            id=uuid4(),
            phone_number="+919876543212",
            preferred_language=LanguageCode.TAMIL,
            location="Chennai, Tamil Nadu, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="user"
        )

    @pytest.fixture
    def trusted_vendor() -> Vendor:
        """Create a trusted test vendor."""
        return Vendor(
            id=uuid4(),
            phone_number="+919876543213",
            preferred_language=LanguageCode.GUJARATI,
            location="Ahmedabad, Gujarat, India",
            tech_literacy_level=TechLiteracyLevel.ADVANCED,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="vendor",
            business_name="Trusted Vendor Co",
            business_type=BusinessType.WHOLESALER,
            rating=Decimal('4.8'),
            total_transactions=150,
            market_reputation=MarketReputation.TRUSTED,
            is_verified_business=True
        )
else:
    # Mock fixtures when app is not available
    @pytest.fixture
    def test_user():
        return MagicMock()
    
    @pytest.fixture
    def test_vendor():
        return MagicMock()
    
    @pytest.fixture
    def auth_headers():
        return {"Authorization": "Bearer mock-token"}
    
    @pytest.fixture
    def vendor_auth_headers():
        return {"Authorization": "Bearer mock-vendor-token"}
    
    @pytest.fixture
    def unverified_user():
        return MagicMock()
    
    @pytest.fixture
    def trusted_vendor():
        return MagicMock()