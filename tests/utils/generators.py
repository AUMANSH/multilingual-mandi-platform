"""
Hypothesis generators for property-based testing.

This module provides custom generators for creating test data that matches
the domain of the Multilingual Mandi Platform, including Indian languages,
locations, products, and user profiles.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from hypothesis import strategies as st
from hypothesis.strategies import composite

# Import enums from models
try:
    from src.mandi_platform.models.enums import (
        LanguageCode,
        ProductCategory,
        QualityGrade,
        MeasurementUnit,
        AvailabilityStatus,
        SeasonalPattern,
        ProductCondition,
        PriceSource,
        MarketConditions,
        BusinessType,
        TechLiteracyLevel,
    )
except ImportError:
    # Fallback for when models aren't available
    class LanguageCode:
        HINDI = "hi"
        ENGLISH = "en"
        TAMIL = "ta"
        TELUGU = "te"
        BENGALI = "bn"
        MARATHI = "mr"
        GUJARATI = "gu"
        KANNADA = "kn"
        MALAYALAM = "ml"
        PUNJABI = "pa"


# Supported languages in the platform
SUPPORTED_LANGUAGES = [
    "hi",  # Hindi
    "en",  # English
    "ta",  # Tamil
    "te",  # Telugu
    "bn",  # Bengali
    "mr",  # Marathi
    "gu",  # Gujarati
    "kn",  # Kannada
    "ml",  # Malayalam
    "pa",  # Punjabi
]

# Indian states and major cities
INDIAN_LOCATIONS = {
    "Delhi": ["New Delhi", "Dwarka", "Rohini", "Lajpat Nagar"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli", "Mangalore"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
    "Punjab": ["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur"],
}

# Product categories and items
PRODUCT_CATEGORIES = {
    "vegetables": [
        "tomatoes", "onions", "potatoes", "carrots", "cabbage",
        "cauliflower", "spinach", "okra", "eggplant", "peppers"
    ],
    "fruits": [
        "apples", "bananas", "oranges", "mangoes", "grapes",
        "pomegranates", "guavas", "papayas", "pineapples", "watermelons"
    ],
    "grains": [
        "rice", "wheat", "barley", "millet", "corn",
        "quinoa", "oats", "ragi", "bajra", "jowar"
    ],
    "spices": [
        "turmeric", "cumin", "coriander", "cardamom", "cinnamon",
        "cloves", "black_pepper", "red_chili", "garam_masala", "mustard_seeds"
    ],
    "dairy": [
        "milk", "yogurt", "cheese", "butter", "ghee",
        "paneer", "cream", "buttermilk", "khoya", "curd"
    ],
}

# Quality grades
QUALITY_GRADES = ["premium", "standard", "economy", "organic", "export_quality"]

# Business types
BUSINESS_TYPES = ["retail", "wholesale", "distributor", "farmer", "cooperative"]

# Tech literacy levels
TECH_LITERACY_LEVELS = ["low", "medium", "high"]

# Measurement units
MEASUREMENT_UNITS = ["kg", "gram", "liter", "piece", "dozen", "quintal", "ton"]


@st.composite
def supported_languages(draw) -> str:
    """Generate supported language codes as strings."""
    return draw(st.sampled_from(SUPPORTED_LANGUAGES))


@st.composite
def language_enum(draw):
    """Generate LanguageCode enum values."""
    try:
        lang_str = draw(st.sampled_from(SUPPORTED_LANGUAGES))
        return LanguageCode(lang_str)
    except:
        return draw(st.sampled_from(SUPPORTED_LANGUAGES))


@st.composite
def product_category_enum(draw):
    """Generate ProductCategory enum values."""
    try:
        categories = [
            ProductCategory.GRAINS,
            ProductCategory.VEGETABLES,
            ProductCategory.FRUITS,
            ProductCategory.SPICES,
            ProductCategory.DAIRY,
            ProductCategory.MEAT,
            ProductCategory.SEAFOOD,
            ProductCategory.PULSES,
            ProductCategory.OILS,
            ProductCategory.TEXTILES,
            ProductCategory.HANDICRAFTS,
            ProductCategory.ELECTRONICS,
            ProductCategory.TOOLS,
            ProductCategory.HOUSEHOLD,
            ProductCategory.OTHER,
        ]
        return draw(st.sampled_from(categories))
    except:
        return draw(st.sampled_from(list(PRODUCT_CATEGORIES.keys())))


@st.composite
def quality_grade_enum(draw):
    """Generate QualityGrade enum values."""
    try:
        grades = [
            QualityGrade.PREMIUM,
            QualityGrade.STANDARD,
            QualityGrade.ECONOMY,
            QualityGrade.ORGANIC,
            QualityGrade.FAIR_TRADE,
        ]
        return draw(st.sampled_from(grades))
    except:
        return draw(st.sampled_from(QUALITY_GRADES))


@st.composite
def measurement_unit_enum(draw):
    """Generate MeasurementUnit enum values."""
    try:
        units = [
            MeasurementUnit.KILOGRAM,
            MeasurementUnit.GRAM,
            MeasurementUnit.LITER,
            MeasurementUnit.PIECE,
            MeasurementUnit.DOZEN,
            MeasurementUnit.QUINTAL,
            MeasurementUnit.TON,
        ]
        return draw(st.sampled_from(units))
    except:
        return draw(st.sampled_from(MEASUREMENT_UNITS))


@st.composite
def availability_status_enum(draw):
    """Generate AvailabilityStatus enum values."""
    try:
        statuses = [
            AvailabilityStatus.AVAILABLE,
            AvailabilityStatus.LIMITED_STOCK,
            AvailabilityStatus.OUT_OF_STOCK,
            AvailabilityStatus.SEASONAL,
            AvailabilityStatus.DISCONTINUED,
            AvailabilityStatus.PRE_ORDER,
        ]
        return draw(st.sampled_from(statuses))
    except:
        return draw(st.sampled_from(["available", "limited_stock", "out_of_stock"]))


@st.composite
def product_condition_enum(draw):
    """Generate ProductCondition enum values."""
    try:
        conditions = [
            ProductCondition.NEW,
            ProductCondition.LIKE_NEW,
            ProductCondition.GOOD,
            ProductCondition.FAIR,
            ProductCondition.REFURBISHED,
        ]
        return draw(st.sampled_from(conditions))
    except:
        return draw(st.sampled_from(["new", "like_new", "good", "fair"]))


@st.composite
def price_source_enum(draw):
    """Generate PriceSource enum values."""
    try:
        sources = [
            PriceSource.VENDOR_LISTED,
            PriceSource.MARKET_API,
            PriceSource.GOVERNMENT_DATA,
            PriceSource.HISTORICAL_AVERAGE,
            PriceSource.ML_PREDICTION,
        ]
        return draw(st.sampled_from(sources))
    except:
        return draw(st.sampled_from(["vendor_listed", "market_api", "government_data"]))


@st.composite
def market_conditions_enum(draw):
    """Generate MarketConditions enum values."""
    try:
        conditions = [
            MarketConditions.NORMAL,
            MarketConditions.HIGH_DEMAND,
            MarketConditions.LOW_DEMAND,
            MarketConditions.SUPPLY_SHORTAGE,
            MarketConditions.OVERSUPPLY,
            MarketConditions.SEASONAL_PEAK,
            MarketConditions.FESTIVAL_RUSH,
        ]
        return draw(st.sampled_from(conditions))
    except:
        return draw(st.sampled_from(["normal", "high_demand", "low_demand"]))


@st.composite
def indian_phone_numbers(draw) -> str:
    """Generate valid Indian phone numbers."""
    # Indian mobile numbers start with +91 and have 10 digits
    number = draw(st.integers(min_value=6000000000, max_value=9999999999))
    return f"+91{number}"


@st.composite
def indian_locations(draw) -> Dict[str, str]:
    """Generate Indian location data."""
    state = draw(st.sampled_from(list(INDIAN_LOCATIONS.keys())))
    city = draw(st.sampled_from(INDIAN_LOCATIONS[state]))
    pincode = draw(st.integers(min_value=100001, max_value=999999))
    
    return {
        "state": state,
        "city": city,
        "pincode": str(pincode)
    }


@st.composite
def product_categories(draw) -> str:
    """Generate product category names."""
    return draw(st.sampled_from(list(PRODUCT_CATEGORIES.keys())))


@st.composite
def product_names(draw, category: Optional[str] = None) -> str:
    """Generate product names, optionally from a specific category."""
    if category and category in PRODUCT_CATEGORIES:
        return draw(st.sampled_from(PRODUCT_CATEGORIES[category]))
    
    # Choose from all categories
    all_products = []
    for products in PRODUCT_CATEGORIES.values():
        all_products.extend(products)
    
    return draw(st.sampled_from(all_products))


@st.composite
def multilingual_text(draw, languages: Optional[List[str]] = None) -> Dict[str, str]:
    """Generate multilingual text dictionary."""
    if languages is None:
        languages = draw(st.lists(
            supported_languages(), 
            min_size=1, 
            max_size=5, 
            unique=True
        ))
    
    text_dict = {}
    base_text = draw(st.text(min_size=1, max_size=100))
    
    for lang in languages:
        # For testing, we'll use the base text with language prefix
        # In real implementation, this would be actual translations
        text_dict[lang] = f"[{lang}] {base_text}"
    
    return text_dict


@st.composite
def prices(draw) -> Decimal:
    """Generate realistic price values."""
    # Prices between 1 and 10000 with 2 decimal places
    price_float = draw(st.floats(min_value=1.0, max_value=10000.0))
    return Decimal(f"{price_float:.2f}")


@st.composite
def user_profiles(draw) -> Dict:
    """Generate user profile data."""
    return {
        "phone_number": draw(indian_phone_numbers()),
        "preferred_language": draw(supported_languages()),
        "location": draw(indian_locations()),
        "tech_literacy_level": draw(st.sampled_from(TECH_LITERACY_LEVELS)),
    }


@st.composite
def vendor_profiles(draw) -> Dict:
    """Generate vendor profile data."""
    base_profile = draw(user_profiles())
    specializations = draw(st.lists(
        product_categories(),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    return {
        **base_profile,
        "business_name": draw(st.text(min_size=5, max_size=50)),
        "business_type": draw(st.sampled_from(BUSINESS_TYPES)),
        "specializations": specializations,
    }


@st.composite
def product_data(draw) -> Dict:
    """Generate product data."""
    category = draw(product_categories())
    product_name = draw(product_names(category))
    
    return {
        "name": draw(multilingual_text()),
        "category": category,
        "description": draw(multilingual_text()),
        "base_price": draw(prices()),
        "unit": draw(st.sampled_from(MEASUREMENT_UNITS)),
        "quality_grade": draw(st.sampled_from(QUALITY_GRADES)),
        "availability": draw(st.sampled_from(["in_stock", "out_of_stock", "limited"])),
    }


@st.composite
def market_data(draw) -> Dict:
    """Generate market data for price discovery."""
    return {
        "product_id": draw(st.uuids()),
        "location": draw(indian_locations()),
        "price": draw(prices()),
        "quality_grade": draw(st.sampled_from(QUALITY_GRADES)),
        "timestamp": draw(st.datetimes(
            min_value=datetime.now() - timedelta(days=30),
            max_value=datetime.now()
        )),
        "source": draw(st.sampled_from(["api", "manual", "scraping", "partner"])),
        "confidence": draw(st.floats(min_value=0.0, max_value=1.0)),
    }


@st.composite
def negotiation_offers(draw) -> Dict:
    """Generate negotiation offer data."""
    return {
        "product_id": draw(st.uuids()),
        "buyer_id": draw(st.uuids()),
        "vendor_id": draw(st.uuids()),
        "offered_price": draw(prices()),
        "quantity": draw(st.integers(min_value=1, max_value=1000)),
        "unit": draw(st.sampled_from(MEASUREMENT_UNITS)),
        "message": draw(st.text(min_size=0, max_size=500)),
        "expires_at": draw(st.datetimes(
            min_value=datetime.now(),
            max_value=datetime.now() + timedelta(days=7)
        )),
    }


@st.composite
def indian_language_text(draw, language: Optional[str] = None) -> str:
    """Generate text that simulates Indian language content."""
    if language is None:
        language = draw(supported_languages())
    
    # For testing purposes, we'll generate text with language-specific patterns
    # In a real implementation, this would use actual language models
    
    base_words = [
        "price", "quality", "fresh", "good", "best", "market", "vendor",
        "buyer", "negotiate", "deal", "offer", "discount", "premium"
    ]
    
    # Add some language-specific markers for testing
    if language == "hi":
        base_words.extend(["दाम", "गुणवत्ता", "ताज़ा", "अच्छा", "बाज़ार"])
    elif language == "ta":
        base_words.extend(["விலை", "தரம்", "புதிய", "நல்ல", "சந்தை"])
    elif language == "te":
        base_words.extend(["ధర", "నాణ్యత", "తాజా", "మంచి", "మార్కెట్"])
    
    # Generate text with 1-10 words
    num_words = draw(st.integers(min_value=1, max_value=10))
    words = draw(st.lists(
        st.sampled_from(base_words),
        min_size=num_words,
        max_size=num_words
    ))
    
    return " ".join(words)


# Strategies for common data types
language_codes = st.sampled_from(SUPPORTED_LANGUAGES)
phone_numbers = indian_phone_numbers()
locations = indian_locations()
user_data = user_profiles()
vendor_data = vendor_profiles()
product_info = product_data()
market_info = market_data()
negotiation_data = negotiation_offers()
multilingual_strings = multilingual_text()
price_values = prices()
quality_grades = st.sampled_from(QUALITY_GRADES)
business_types = st.sampled_from(BUSINESS_TYPES)
tech_levels = st.sampled_from(TECH_LITERACY_LEVELS)
measurement_units = st.sampled_from(MEASUREMENT_UNITS)


@st.composite
def user_session_data(draw) -> Dict[str, Any]:
    """Generate user session data for testing."""
    # Use fixed datetime range to avoid flaky strategy issues
    base_time = datetime(2024, 1, 1)
    max_time = datetime(2024, 12, 31)
    
    return {
        "user_id": str(draw(st.uuids())),
        "preferred_language": draw(supported_languages()),
        "location": draw(indian_locations()),
        "tech_literacy_level": draw(st.sampled_from(TECH_LITERACY_LEVELS)),
        "session_id": str(draw(st.uuids())),
        "login_time": draw(st.datetimes(
            min_value=base_time,
            max_value=max_time
        )).isoformat(),
        "cart_items": draw(st.lists(
            st.dictionaries(
                keys=st.sampled_from(["product_id", "quantity", "price"]),
                values=st.one_of(
                    st.uuids().map(str),
                    st.integers(min_value=1, max_value=100),
                    prices().map(str)
                )
            ),
            min_size=0,
            max_size=5
        )),
        "search_history": draw(st.lists(
            st.text(min_size=1, max_size=50),
            min_size=0,
            max_size=10
        )),
        "notification_preferences": {
            "email": draw(st.booleans()),
            "sms": draw(st.booleans()),
            "push": draw(st.booleans())
        }
    }


@st.composite
def ui_element_keys(draw) -> Dict[str, str]:
    """Generate UI element keys and their default text."""
    # Common UI elements in a trading platform
    possible_elements = {
        "welcome_message": "Welcome to Mandi Platform",
        "login_button": "Login",
        "logout_button": "Logout",
        "search_placeholder": "Search products...",
        "price_label": "Price",
        "quantity_label": "Quantity",
        "quality_label": "Quality",
        "vendor_label": "Vendor",
        "location_label": "Location",
        "add_to_cart": "Add to Cart",
        "buy_now": "Buy Now",
        "negotiate_button": "Start Negotiation",
        "filter_button": "Filter",
        "sort_button": "Sort",
        "profile_menu": "Profile",
        "settings_menu": "Settings",
        "help_button": "Help",
        "contact_us": "Contact Us",
        "terms_link": "Terms & Conditions",
        "privacy_link": "Privacy Policy",
        "language_selector": "Select Language",
        "currency_selector": "Currency",
        "notification_bell": "Notifications",
        "market_rates": "Market Rates",
        "trending_products": "Trending Products",
        "my_orders": "My Orders",
        "order_history": "Order History",
        "payment_methods": "Payment Methods",
        "shipping_address": "Shipping Address",
        "product_reviews": "Reviews",
        "seller_rating": "Seller Rating",
        "delivery_time": "Delivery Time",
        "return_policy": "Return Policy"
    }
    
    # Select a random subset of elements
    num_elements = draw(st.integers(min_value=1, max_value=min(10, len(possible_elements))))
    selected_keys = draw(st.lists(
        st.sampled_from(list(possible_elements.keys())),
        min_size=num_elements,
        max_size=num_elements,
        unique=True
    ))
    
    return {key: possible_elements[key] for key in selected_keys}


@st.composite
def market_context_data(draw) -> Dict[str, Any]:
    """Generate market context data for contextual translations."""
    return {
        "product_category": draw(product_categories()),
        "negotiation_phase": draw(st.sampled_from([
            "initial", "counter_offer", "final_offer", "agreement", "dispute"
        ])),
        "relationship_type": draw(st.sampled_from([
            "new_customer", "returning_customer", "vip_customer", "bulk_buyer"
        ])),
        "regional_context": draw(st.sampled_from([
            "urban", "rural", "semi_urban", "metropolitan"
        ])),
        "seasonal_factor": draw(st.sampled_from([
            "peak_season", "off_season", "festival_season", "harvest_season"
        ])),
        "market_conditions": draw(st.sampled_from([
            "high_demand", "low_demand", "stable", "volatile"
        ]))
    }