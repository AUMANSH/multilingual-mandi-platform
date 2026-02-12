"""
Tests for Product CRUD operations.

This module tests the ProductCRUD, ProductCategoryCRUD, and PriceHistoryCRUD classes.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta

from src.mandi_platform.crud.product import ProductCRUD, ProductCategoryCRUD, PriceHistoryCRUD
from src.mandi_platform.models import (
    Product,
    ProductCategoryModel,
    PriceHistory,
    Vendor,
    LanguageCode,
    ProductCategory,
    QualityGrade,
    MeasurementUnit,
    AvailabilityStatus,
    PriceSource,
    MarketConditions,
    BusinessType,
)
from tests.utils.database import get_test_db_session
from tests.utils.factories import create_test_vendor


@pytest.mark.asyncio
async def test_product_crud_create():
    """Test product creation via CRUD."""
    async with get_test_db_session() as db:
        # Create test vendor and category
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.GRAINS,
            names={"en": "Grains", "hi": "अनाज"},
            descriptions={"en": "Various grains"}
        )
        
        # Create product
        product_crud = ProductCRUD(db)
        product = await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category.id,
            names={"en": "Basmati Rice", "hi": "बासमती चावल"},
            descriptions={"en": "Premium basmati rice", "hi": "प्रीमियम बासमती चावल"},
            base_price=Decimal("120.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            quality_grade=QualityGrade.PREMIUM.value,
            location={"city": "Delhi", "state": "Delhi", "country": "India"},
            stock_quantity=Decimal("100"),
            tags=["premium", "basmati"],
            search_keywords=["rice", "basmati", "premium"]
        )
        
        assert product is not None
        assert product.vendor_id == vendor.id
        assert product.category_id == category.id
        assert product.get_name(LanguageCode.ENGLISH) == "Basmati Rice"
        assert product.get_name(LanguageCode.HINDI) == "बासमती चावल"
        assert product.base_price == Decimal("120.00")
        assert product.unit == MeasurementUnit.KILOGRAM
        assert product.quality_grade == QualityGrade.PREMIUM
        assert product.stock_quantity == Decimal("100")


@pytest.mark.asyncio
async def test_product_crud_get():
    """Test product retrieval via CRUD."""
    async with get_test_db_session() as db:
        # Create test data
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.VEGETABLES,
            names={"en": "Vegetables"}
        )
        
        product_crud = ProductCRUD(db)
        created_product = await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category.id,
            names={"en": "Tomatoes"},
            descriptions={"en": "Fresh tomatoes"},
            base_price=Decimal("40.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            location={"city": "Mumbai"}
        )
        
        # Test get by ID
        retrieved_product = await product_crud.get_product(created_product.id)
        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.get_name() == "Tomatoes"
        
        # Test get with vendor
        product_with_vendor = await product_crud.get_product_with_vendor(created_product.id)
        assert product_with_vendor is not None
        assert product_with_vendor.vendor is not None
        assert product_with_vendor.vendor.id == vendor.id


@pytest.mark.asyncio
async def test_product_crud_update():
    """Test product update via CRUD."""
    async with get_test_db_session() as db:
        # Create test data
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.FRUITS,
            names={"en": "Fruits"}
        )
        
        product_crud = ProductCRUD(db)
        product = await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category.id,
            names={"en": "Apples"},
            descriptions={"en": "Fresh apples"},
            base_price=Decimal("80.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            location={"city": "Shimla"}
        )
        
        # Update product
        updated_product = await product_crud.update_product(
            product.id,
            base_price=Decimal("85.00"),
            names={"en": "Premium Apples", "hi": "प्रीमियम सेब"},
            is_featured=True
        )
        
        assert updated_product is not None
        assert updated_product.base_price == Decimal("85.00")
        assert updated_product.get_name(LanguageCode.ENGLISH) == "Premium Apples"
        assert updated_product.get_name(LanguageCode.HINDI) == "प्रीमियम सेब"
        assert updated_product.is_featured is True


@pytest.mark.asyncio
async def test_product_crud_stock_update():
    """Test stock update via CRUD."""
    async with get_test_db_session() as db:
        # Create test data
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.SPICES,
            names={"en": "Spices"}
        )
        
        product_crud = ProductCRUD(db)
        product = await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category.id,
            names={"en": "Turmeric"},
            descriptions={"en": "Pure turmeric powder"},
            base_price=Decimal("200.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            location={"city": "Chennai"},
            stock_quantity=Decimal("50")
        )
        
        # Update stock to low level
        updated_product = await product_crud.update_stock(product.id, Decimal("5"))
        assert updated_product is not None
        assert updated_product.stock_quantity == Decimal("5")
        assert updated_product.availability_status == AvailabilityStatus.LIMITED_STOCK
        
        # Update stock to zero
        updated_product = await product_crud.update_stock(product.id, Decimal("0"))
        assert updated_product.stock_quantity == Decimal("0")
        assert updated_product.availability_status == AvailabilityStatus.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_product_crud_get_by_vendor():
    """Test getting products by vendor."""
    async with get_test_db_session() as db:
        # Create test data
        vendor1 = await create_test_vendor(db)
        vendor2 = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.DAIRY,
            names={"en": "Dairy"}
        )
        
        product_crud = ProductCRUD(db)
        
        # Create products for vendor1
        product1 = await product_crud.create_product(
            vendor_id=vendor1.id,
            category_id=category.id,
            names={"en": "Milk"},
            descriptions={"en": "Fresh milk"},
            base_price=Decimal("50.00"),
            unit=MeasurementUnit.LITER.value,
            location={"city": "Pune"}
        )
        
        product2 = await product_crud.create_product(
            vendor_id=vendor1.id,
            category_id=category.id,
            names={"en": "Yogurt"},
            descriptions={"en": "Fresh yogurt"},
            base_price=Decimal("60.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            location={"city": "Pune"}
        )
        
        # Create product for vendor2
        product3 = await product_crud.create_product(
            vendor_id=vendor2.id,
            category_id=category.id,
            names={"en": "Cheese"},
            descriptions={"en": "Fresh cheese"},
            base_price=Decimal("300.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            location={"city": "Mumbai"}
        )
        
        # Get products by vendor1
        vendor1_products = await product_crud.get_products_by_vendor(vendor1.id)
        assert len(vendor1_products) == 2
        product_names = [p.get_name() for p in vendor1_products]
        assert "Milk" in product_names
        assert "Yogurt" in product_names
        
        # Get products by vendor2
        vendor2_products = await product_crud.get_products_by_vendor(vendor2.id)
        assert len(vendor2_products) == 1
        assert vendor2_products[0].get_name() == "Cheese"


@pytest.mark.asyncio
async def test_product_crud_get_by_category():
    """Test getting products by category."""
    async with get_test_db_session() as db:
        # Create test data
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category1 = await category_crud.create_category(
            category_enum=ProductCategory.OILS,
            names={"en": "Oils"}
        )
        category2 = await category_crud.create_category(
            category_enum=ProductCategory.PULSES,
            names={"en": "Pulses"}
        )
        
        product_crud = ProductCRUD(db)
        
        # Create products in category1
        await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category1.id,
            names={"en": "Coconut Oil"},
            descriptions={"en": "Pure coconut oil"},
            base_price=Decimal("150.00"),
            unit=MeasurementUnit.LITER.value,
            location={"city": "Kerala"}
        )
        
        await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category1.id,
            names={"en": "Mustard Oil"},
            descriptions={"en": "Pure mustard oil"},
            base_price=Decimal("120.00"),
            unit=MeasurementUnit.LITER.value,
            location={"city": "Bengal"}
        )
        
        # Create product in category2
        await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category2.id,
            names={"en": "Lentils"},
            descriptions={"en": "Red lentils"},
            base_price=Decimal("90.00"),
            unit=MeasurementUnit.KILOGRAM.value,
            location={"city": "Punjab"}
        )
        
        # Get products by category1
        category1_products = await product_crud.get_products_by_category(category1.id)
        assert len(category1_products) == 2
        product_names = [p.get_name() for p in category1_products]
        assert "Coconut Oil" in product_names
        assert "Mustard Oil" in product_names
        
        # Get products by category2
        category2_products = await product_crud.get_products_by_category(category2.id)
        assert len(category2_products) == 1
        assert category2_products[0].get_name() == "Lentils"


@pytest.mark.asyncio
async def test_product_crud_delete():
    """Test product deletion (soft delete)."""
    async with get_test_db_session() as db:
        # Create test data
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.TEXTILES,
            names={"en": "Textiles"}
        )
        
        product_crud = ProductCRUD(db)
        product = await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category.id,
            names={"en": "Cotton Fabric"},
            descriptions={"en": "Pure cotton fabric"},
            base_price=Decimal("500.00"),
            unit=MeasurementUnit.PIECE.value,
            location={"city": "Gujarat"}
        )
        
        # Verify product is active
        assert product.is_active is True
        
        # Delete product
        success = await product_crud.delete_product(product.id)
        assert success is True
        
        # Verify product is soft deleted
        deleted_product = await product_crud.get_product(product.id)
        assert deleted_product.is_active is False


@pytest.mark.asyncio
async def test_product_category_crud():
    """Test product category CRUD operations."""
    async with get_test_db_session() as db:
        category_crud = ProductCategoryCRUD(db)
        
        # Create category
        category = await category_crud.create_category(
            category_enum=ProductCategory.HANDICRAFTS,
            names={"en": "Handicrafts", "hi": "हस्तशिल्प"},
            descriptions={"en": "Traditional handicrafts", "hi": "पारंपरिक हस्तशिल्प"}
        )
        
        assert category is not None
        assert category.category_enum == ProductCategory.HANDICRAFTS
        assert category.get_name(LanguageCode.ENGLISH) == "Handicrafts"
        assert category.get_name(LanguageCode.HINDI) == "हस्तशिल्प"
        
        # Get category by ID
        retrieved_category = await category_crud.get_category(category.id)
        assert retrieved_category is not None
        assert retrieved_category.id == category.id
        
        # Get category by enum
        enum_category = await category_crud.get_category_by_enum(ProductCategory.HANDICRAFTS)
        assert enum_category is not None
        assert enum_category.id == category.id
        
        # Update category
        updated_category = await category_crud.update_category(
            category.id,
            names={"en": "Arts & Handicrafts", "hi": "कला और हस्तशिल्प"},
            sort_order=10
        )
        
        assert updated_category is not None
        assert updated_category.get_name(LanguageCode.ENGLISH) == "Arts & Handicrafts"
        assert updated_category.sort_order == 10


@pytest.mark.asyncio
async def test_price_history_crud():
    """Test price history CRUD operations."""
    async with get_test_db_session() as db:
        # Create test product
        vendor = await create_test_vendor(db)
        
        category_crud = ProductCategoryCRUD(db)
        category = await category_crud.create_category(
            category_enum=ProductCategory.ELECTRONICS,
            names={"en": "Electronics"}
        )
        
        product_crud = ProductCRUD(db)
        product = await product_crud.create_product(
            vendor_id=vendor.id,
            category_id=category.id,
            names={"en": "Mobile Phone"},
            descriptions={"en": "Smartphone"},
            base_price=Decimal("15000.00"),
            unit=MeasurementUnit.PIECE.value,
            location={"city": "Bangalore"}
        )
        
        # Create price history
        price_crud = PriceHistoryCRUD(db)
        price_history = await price_crud.record_price(
            product_id=product.id,
            price=Decimal("14500.00"),
            quality_grade=QualityGrade.STANDARD,
            location={"city": "Bangalore", "state": "Karnataka"},
            source=PriceSource.VENDOR_LISTED,
            market_conditions=MarketConditions.NORMAL,
            quantity_range="1 piece",
            notes="Regular pricing"
        )
        
        assert price_history is not None
        assert price_history.product_id == product.id
        assert price_history.price == Decimal("14500.00")
        assert price_history.quality_grade == QualityGrade.STANDARD
        assert price_history.source == PriceSource.VENDOR_LISTED
        
        # Record another price
        await price_crud.record_price(
            product_id=product.id,
            price=Decimal("14000.00"),
            quality_grade=QualityGrade.STANDARD,
            location={"city": "Bangalore", "state": "Karnataka"},
            source=PriceSource.MARKET_API,
            market_conditions=MarketConditions.HIGH_DEMAND
        )
        
        # Get price history
        history = await price_crud.get_price_history(product.id, days=30)
        assert len(history) == 2
        
        # Get average price
        avg_price = await price_crud.get_average_price(product.id, days=7)
        assert avg_price is not None
        assert avg_price == Decimal("14250.00")  # Average of 14500 and 14000