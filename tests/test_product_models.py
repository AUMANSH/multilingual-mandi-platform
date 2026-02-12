"""
Tests for Product models.

This module tests the Product, ProductCategory, and PriceHistory models
with their relationships and methods.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.mandi_platform.models import (
    Product,
    ProductCategoryModel,
    PriceHistory,
    LanguageCode,
    ProductCategory,
    QualityGrade,
    MeasurementUnit,
    AvailabilityStatus,
    SeasonalPattern,
    ProductCondition,
    PriceSource,
    MarketConditions,
)
from tests.utils.database import get_test_db_session


@pytest.mark.asyncio
async def test_product_creation():
    """Test basic product creation."""
    async with get_test_db_session() as db:
        # Create a vendor first (assuming it exists from previous tests)
        vendor_id = uuid4()
        category_id = uuid4()
        
        product = Product(
            vendor_id=vendor_id,
            category_id=category_id,
            names={"en": "Test Product", "hi": "परीक्षण उत्पाद"},
            descriptions={"en": "A test product", "hi": "एक परीक्षण उत्पाद"},
            base_price=Decimal("100.50"),
            unit=MeasurementUnit.KILOGRAM,
            location={"city": "Mumbai", "state": "Maharashtra"}
        )
        
        db.add(product)
        await db.commit()
        await db.refresh(product)
        
        assert product.id is not None
        assert product.vendor_id == vendor_id
        assert product.category_id == category_id
        assert product.base_price == Decimal("100.50")
        assert product.unit == MeasurementUnit.KILOGRAM
        assert product.quality_grade == QualityGrade.STANDARD  # Default
        assert product.availability_status == AvailabilityStatus.AVAILABLE  # Default
        assert product.is_active is True  # Default


@pytest.mark.asyncio
async def test_product_multilingual_methods():
    """Test multilingual text methods."""
    async with get_test_db_session() as db:
        product = Product(
            vendor_id=uuid4(),
            category_id=uuid4(),
            names={"en": "Rice", "hi": "चावल", "ta": "அரிசி"},
            descriptions={"en": "Premium rice", "hi": "प्रीमियम चावल"},
            base_price=Decimal("50.00"),
            unit=MeasurementUnit.KILOGRAM,
            location={}
        )
        
        # Test getting names in different languages
        assert product.get_name(LanguageCode.ENGLISH) == "Rice"
        assert product.get_name(LanguageCode.HINDI) == "चावल"
        assert product.get_name(LanguageCode.TAMIL) == "அரிசி"
        
        # Test fallback to English for missing language
        assert product.get_name(LanguageCode.BENGALI) == "Rice"  # Falls back to English
        
        # Test setting new name
        product.set_name(LanguageCode.BENGALI, "ভাত")
        assert product.get_name(LanguageCode.BENGALI) == "ভাত"
        
        # Test descriptions
        assert product.get_description(LanguageCode.ENGLISH) == "Premium rice"
        assert product.get_description(LanguageCode.HINDI) == "प्रीमियम चावल"
        
        # Test setting new description
        product.set_description(LanguageCode.TAMIL, "பிரீமியம் அரிசி")
        assert product.get_description(LanguageCode.TAMIL) == "பிரீமியம் அரிசி"


@pytest.mark.asyncio
async def test_product_stock_management():
    """Test stock quantity management."""
    async with get_test_db_session() as db:
        product = Product(
            vendor_id=uuid4(),
            category_id=uuid4(),
            names={"en": "Test Product"},
            descriptions={"en": "Test"},
            base_price=Decimal("100.00"),
            unit=MeasurementUnit.KILOGRAM,
            location={},
            stock_quantity=Decimal("100")
        )
        
        # Test initial stock
        assert product.stock_quantity == Decimal("100")
        assert product.availability_status == AvailabilityStatus.AVAILABLE
        
        # Test updating to low stock
        product.update_stock(Decimal("5"))
        assert product.stock_quantity == Decimal("5")
        assert product.availability_status == AvailabilityStatus.LIMITED_STOCK
        
        # Test updating to out of stock
        product.update_stock(Decimal("0"))
        assert product.stock_quantity == Decimal("0")
        assert product.availability_status == AvailabilityStatus.OUT_OF_STOCK
        
        # Test restocking
        product.update_stock(Decimal("50"))
        assert product.stock_quantity == Decimal("50")
        assert product.availability_status == AvailabilityStatus.AVAILABLE


@pytest.mark.asyncio
async def test_product_attributes_and_tags():
    """Test product attributes and tags management."""
    async with get_test_db_session() as db:
        product = Product(
            vendor_id=uuid4(),
            category_id=uuid4(),
            names={"en": "Test Product"},
            descriptions={"en": "Test"},
            base_price=Decimal("100.00"),
            unit=MeasurementUnit.KILOGRAM,
            location={}
        )
        
        # Test attributes
        product.set_attribute("color", "red")
        product.set_attribute("weight", "1kg")
        assert product.get_attribute("color") == "red"
        assert product.get_attribute("weight") == "1kg"
        assert product.get_attribute("nonexistent") is None
        assert product.get_attribute("nonexistent", "default") == "default"
        
        # Test tags
        product.add_tag("organic")
        product.add_tag("premium")
        assert "organic" in product.tags
        assert "premium" in product.tags
        
        # Test duplicate tag (should not be added)
        product.add_tag("organic")
        assert product.tags.count("organic") == 1
        
        # Test removing tag
        product.remove_tag("premium")
        assert "premium" not in product.tags
        assert "organic" in product.tags
        
        # Test search keywords
        product.add_search_keyword("rice")
        product.add_search_keyword("basmati")
        assert "rice" in product.search_keywords
        assert "basmati" in product.search_keywords


@pytest.mark.asyncio
async def test_product_elasticsearch_document():
    """Test Elasticsearch document conversion."""
    async with get_test_db_session() as db:
        product = Product(
            vendor_id=uuid4(),
            category_id=uuid4(),
            names={"en": "Rice", "hi": "चावल"},
            descriptions={"en": "Premium rice", "hi": "प्रीमियम चावल"},
            base_price=Decimal("50.00"),
            unit=MeasurementUnit.KILOGRAM,
            quality_grade=QualityGrade.PREMIUM,
            location={"city": "Mumbai", "state": "Maharashtra"},
            tags=["organic", "premium"],
            search_keywords=["rice", "basmati"]
        )
        
        doc = product.to_elasticsearch_document()
        
        assert doc["id"] == str(product.id)
        assert doc["names"] == {"en": "Rice", "hi": "चावल"}
        assert doc["descriptions"] == {"en": "Premium rice", "hi": "प्रीमियम चावल"}
        assert doc["base_price"] == 50.0
        assert doc["unit"] == "kg"
        assert doc["quality_grade"] == "premium"
        assert doc["location"] == {"city": "Mumbai", "state": "Maharashtra"}
        assert doc["tags"] == ["organic", "premium"]
        assert doc["search_keywords"] == ["rice", "basmati"]
        assert doc["is_active"] is True


@pytest.mark.asyncio
async def test_product_properties():
    """Test product computed properties."""
    async with get_test_db_session() as db:
        # Test available product
        product = Product(
            vendor_id=uuid4(),
            category_id=uuid4(),
            names={"en": "Test Product"},
            descriptions={"en": "Test"},
            base_price=Decimal("100.00"),
            unit=MeasurementUnit.KILOGRAM,
            location={},
            is_active=True,
            availability_status=AvailabilityStatus.AVAILABLE
        )
        
        assert product.is_available is True
        assert product.display_price == "₹100.00 per kg"
        
        # Test inactive product
        product.is_active = False
        assert product.is_available is False
        
        # Test out of stock product
        product.is_active = True
        product.availability_status = AvailabilityStatus.OUT_OF_STOCK
        assert product.is_available is False


@pytest.mark.asyncio
async def test_product_category_creation():
    """Test product category creation."""
    async with get_test_db_session() as db:
        category = ProductCategoryModel(
            category_enum=ProductCategory.GRAINS,
            names={"en": "Grains", "hi": "अनाज"},
            descriptions={"en": "Various grains", "hi": "विभिन्न अनाज"}
        )
        
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        assert category.id is not None
        assert category.category_enum == ProductCategory.GRAINS
        assert category.is_active is True
        assert category.sort_order == 0


@pytest.mark.asyncio
async def test_product_category_multilingual():
    """Test product category multilingual methods."""
    async with get_test_db_session() as db:
        category = ProductCategoryModel(
            category_enum=ProductCategory.VEGETABLES,
            names={"en": "Vegetables", "hi": "सब्जियां", "ta": "காய்கறிகள்"},
            descriptions={"en": "Fresh vegetables", "hi": "ताजी सब्जियां"}
        )
        
        # Test getting names
        assert category.get_name(LanguageCode.ENGLISH) == "Vegetables"
        assert category.get_name(LanguageCode.HINDI) == "सब्जियां"
        assert category.get_name(LanguageCode.TAMIL) == "காய்கறிகள்"
        
        # Test setting names
        category.set_name(LanguageCode.BENGALI, "সবজি")
        assert category.get_name(LanguageCode.BENGALI) == "সবজি"
        
        # Test descriptions
        assert category.get_description(LanguageCode.ENGLISH) == "Fresh vegetables"
        assert category.get_description(LanguageCode.HINDI) == "ताजी सब्जियां"


@pytest.mark.asyncio
async def test_price_history_creation():
    """Test price history creation."""
    async with get_test_db_session() as db:
        product_id = uuid4()
        
        price_history = PriceHistory(
            product_id=product_id,
            price=Decimal("45.50"),
            quality_grade=QualityGrade.PREMIUM,
            location={"city": "Delhi", "state": "Delhi"},
            source=PriceSource.MARKET_API,
            market_conditions=MarketConditions.HIGH_DEMAND,
            quantity_range="1-10 kg",
            notes="Festival season pricing"
        )
        
        db.add(price_history)
        await db.commit()
        await db.refresh(price_history)
        
        assert price_history.id is not None
        assert price_history.product_id == product_id
        assert price_history.price == Decimal("45.50")
        assert price_history.quality_grade == QualityGrade.PREMIUM
        assert price_history.source == PriceSource.MARKET_API
        assert price_history.market_conditions == MarketConditions.HIGH_DEMAND
        assert price_history.currency == "INR"  # Default
        assert price_history.recorded_at is not None