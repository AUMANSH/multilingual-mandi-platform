"""
Factory classes for creating test data using factory_boy.

These factories provide a convenient way to create model instances
for testing with realistic data.
"""

import factory
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from uuid import uuid4

from factory import Faker, SubFactory, LazyAttribute, LazyFunction


class LocationFactory(factory.DictFactory):
    """Factory for location data."""
    
    state = factory.Faker('random_element', elements=[
        'Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'West Bengal',
        'Gujarat', 'Rajasthan', 'Punjab', 'Telangana', 'Kerala'
    ])
    
    city = factory.LazyAttribute(lambda obj: {
        'Delhi': 'New Delhi',
        'Maharashtra': 'Mumbai',
        'Karnataka': 'Bangalore',
        'Tamil Nadu': 'Chennai',
        'West Bengal': 'Kolkata',
        'Gujarat': 'Ahmedabad',
        'Rajasthan': 'Jaipur',
        'Punjab': 'Chandigarh',
        'Telangana': 'Hyderabad',
        'Kerala': 'Kochi',
    }.get(obj.state, 'Unknown'))
    
    pincode = factory.Sequence(lambda n: str(100001 + n))


class MultilingualTextFactory(factory.DictFactory):
    """Factory for multilingual text data."""
    
    en = factory.Faker('sentence', nb_words=4)
    hi = factory.LazyAttribute(lambda obj: f"[Hindi] {obj.en}")
    ta = factory.LazyAttribute(lambda obj: f"[Tamil] {obj.en}")


class UserDataFactory(factory.DictFactory):
    """Factory for user data."""
    
    phone_number = factory.Sequence(lambda n: f"+91{6000000000 + n}")
    preferred_language = factory.Faker('random_element', elements=[
        'hi', 'en', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa'
    ])
    location = SubFactory(LocationFactory)
    tech_literacy_level = factory.Faker('random_element', elements=[
        'low', 'medium', 'high'
    ])


class VendorDataFactory(UserDataFactory):
    """Factory for vendor data."""
    
    business_name = factory.Faker('company')
    business_type = factory.Faker('random_element', elements=[
        'retail', 'wholesale', 'distributor', 'farmer', 'cooperative'
    ])
    specializations = factory.LazyFunction(
        lambda: ['vegetables', 'fruits']  # Simple fixed list for testing
    )


class ProductDataFactory(factory.DictFactory):
    """Factory for product data."""
    
    name = SubFactory(MultilingualTextFactory)
    category = factory.Faker('random_element', elements=[
        'vegetables', 'fruits', 'grains', 'spices', 'dairy'
    ])
    description = SubFactory(MultilingualTextFactory)
    base_price = factory.LazyFunction(
        lambda: Decimal(f"{50 + (hash(str(datetime.now())) % 5000) / 100:.2f}")
    )
    unit = factory.Faker('random_element', elements=[
        'kg', 'gram', 'liter', 'piece', 'dozen', 'quintal', 'ton'
    ])
    quality_grade = factory.Faker('random_element', elements=[
        'premium', 'standard', 'economy', 'organic', 'export_quality'
    ])
    availability = factory.Faker('random_element', elements=[
        'in_stock', 'out_of_stock', 'limited'
    ])


class MarketDataFactory(factory.DictFactory):
    """Factory for market data."""
    
    product_id = factory.LazyFunction(uuid4)
    location = SubFactory(LocationFactory)
    price = factory.LazyFunction(
        lambda: Decimal(f"{factory.Faker('random_int', min=100, max=10000).generate() / 100:.2f}")
    )
    quality_grade = factory.Faker('random_element', elements=[
        'premium', 'standard', 'economy', 'organic', 'export_quality'
    ])
    timestamp = factory.LazyFunction(
        lambda: datetime.now() - timedelta(
            days=factory.Faker('random_int', min=0, max=30).generate()
        )
    )
    source = factory.Faker('random_element', elements=[
        'api', 'manual', 'scraping', 'partner'
    ])
    confidence = factory.Faker('random_int', min=70, max=100)


class NegotiationOfferFactory(factory.DictFactory):
    """Factory for negotiation offer data."""
    
    product_id = factory.LazyFunction(uuid4)
    buyer_id = factory.LazyFunction(uuid4)
    vendor_id = factory.LazyFunction(uuid4)
    offered_price = factory.LazyFunction(
        lambda: Decimal(f"{factory.Faker('random_int', min=100, max=10000).generate() / 100:.2f}")
    )
    quantity = factory.Faker('random_int', min=1, max=100)
    unit = factory.Faker('random_element', elements=[
        'kg', 'gram', 'liter', 'piece', 'dozen'
    ])
    message = factory.Faker('sentence', nb_words=10)
    expires_at = factory.LazyFunction(
        lambda: datetime.now() + timedelta(
            days=factory.Faker('random_int', min=1, max=7).generate()
        )
    )


class TranslationCacheFactory(factory.DictFactory):
    """Factory for translation cache data."""
    
    source_text = factory.Faker('sentence', nb_words=6)
    source_language = factory.Faker('random_element', elements=[
        'hi', 'en', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa'
    ])
    target_language = factory.Faker('random_element', elements=[
        'hi', 'en', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa'
    ])
    translated_text = factory.LazyAttribute(
        lambda obj: f"[{obj.target_language}] {obj.source_text}"
    )
    context_hash = factory.LazyFunction(
        lambda: factory.Faker('sha256').generate()
    )
    confidence_score = factory.Faker('random_int', min=70, max=100)
    created_at = factory.LazyFunction(datetime.now)
    usage_count = factory.Faker('random_int', min=1, max=100)


# Utility functions for creating test data

async def create_test_vendor(db_session) -> Any:
    """Create a test vendor in the database."""
    from src.mandi_platform.models import Vendor, BusinessType, LanguageCode
    from src.mandi_platform.crud.user import UserCRUD
    
    user_crud = UserCRUD(db_session)
    vendor_data = VendorDataFactory()
    
    vendor = await user_crud.create_vendor(
        phone_number=vendor_data['phone_number'],
        preferred_language=LanguageCode(vendor_data['preferred_language']),
        location=f"{vendor_data['location']['city']}, {vendor_data['location']['state']}",
        business_name=vendor_data['business_name'],
        business_type=BusinessType.SMALL_BUSINESS,
    )
    
    return vendor


async def create_test_product_category(db_session, category_enum=None) -> Any:
    """Create a test product category in the database."""
    from src.mandi_platform.crud.product import ProductCategoryCRUD
    from src.mandi_platform.models import ProductCategory
    
    if category_enum is None:
        category_enum = ProductCategory.VEGETABLES
    
    category_crud = ProductCategoryCRUD(db_session)
    category = await category_crud.create_category(
        category_enum=category_enum,
        names={"en": category_enum.value.title(), "hi": f"[Hindi] {category_enum.value.title()}"},
        descriptions={"en": f"Category for {category_enum.value}", "hi": f"[Hindi] Category for {category_enum.value}"}
    )
    
    return category


async def create_test_product(db_session, vendor=None, category=None) -> Any:
    """Create a test product in the database."""
    from src.mandi_platform.crud.product import ProductCRUD
    from src.mandi_platform.models import MeasurementUnit, QualityGrade
    
    if vendor is None:
        vendor = await create_test_vendor(db_session)
    
    if category is None:
        category = await create_test_product_category(db_session)
    
    product_data = ProductDataFactory()
    product_crud = ProductCRUD(db_session)
    
    product = await product_crud.create_product(
        vendor_id=vendor.id,
        category_id=category.id,
        names=product_data['name'],
        descriptions=product_data['description'],
        base_price=product_data['base_price'],
        unit=MeasurementUnit.KILOGRAM.value,
        quality_grade=QualityGrade.STANDARD.value,
        location=product_data.get('location', {"city": "Mumbai", "state": "Maharashtra"}),
        stock_quantity=Decimal("100"),
        tags=["test", "sample"],
        search_keywords=["test", "product"]
    )
    
    return product


def create_test_users(count: int = 5) -> list[Dict[str, Any]]:
    """Create multiple test users."""
    return [UserDataFactory() for _ in range(count)]


def create_test_vendors(count: int = 3) -> list[Dict[str, Any]]:
    """Create multiple test vendors."""
    return [VendorDataFactory() for _ in range(count)]


def create_test_products(count: int = 10) -> list[Dict[str, Any]]:
    """Create multiple test products."""
    return [ProductDataFactory() for _ in range(count)]


def create_test_market_data(count: int = 20) -> list[Dict[str, Any]]:
    """Create multiple market data entries."""
    return [MarketDataFactory() for _ in range(count)]


def create_negotiation_scenario() -> Dict[str, Any]:
    """Create a complete negotiation scenario with buyer, vendor, and product."""
    buyer = UserDataFactory()
    vendor = VendorDataFactory()
    product = ProductDataFactory()
    offer = NegotiationOfferFactory()
    
    return {
        "buyer": buyer,
        "vendor": vendor,
        "product": product,
        "offer": offer,
    }


def create_multilingual_product_catalog(count: int = 50) -> list[Dict[str, Any]]:
    """Create a diverse product catalog with multilingual data."""
    products = []
    categories = ['vegetables', 'fruits', 'grains', 'spices', 'dairy']
    
    for _ in range(count):
        product = ProductDataFactory()
        # Ensure good distribution across categories
        product['category'] = factory.Faker('random_element', elements=categories).generate()
        products.append(product)
    
    return products


def create_price_history_data(product_id: str, days: int = 30) -> list[Dict[str, Any]]:
    """Create price history data for a specific product."""
    history = []
    base_price = Decimal('50.00')
    
    for day in range(days):
        # Simulate price fluctuations
        price_change = factory.Faker('random_int', min=-500, max=500).generate() / 100
        current_price = max(Decimal('1.00'), base_price + Decimal(str(price_change)))
        
        history.append({
            'product_id': product_id,
            'price': current_price,
            'timestamp': datetime.now() - timedelta(days=day),
            'location': LocationFactory(),
            'quality_grade': factory.Faker('random_element', elements=[
                'premium', 'standard', 'economy'
            ]).generate(),
            'source': 'api',
            'confidence': factory.Faker('random_int', min=80, max=100).generate(),
        })
        
        base_price = current_price
    
    return history