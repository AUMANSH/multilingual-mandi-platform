"""
Custom assertion helpers for testing the Multilingual Mandi Platform.

These utilities provide domain-specific assertions that make tests
more readable and maintainable.
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


def assert_valid_language_code(language_code: str) -> None:
    """Assert that a language code is supported by the platform."""
    supported_languages = {
        'hi', 'en', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa'
    }
    assert language_code in supported_languages, (
        f"Language code '{language_code}' is not supported. "
        f"Supported languages: {sorted(supported_languages)}"
    )


def assert_valid_phone_number(phone_number: str) -> None:
    """Assert that a phone number follows Indian format."""
    assert phone_number.startswith('+91'), (
        f"Phone number '{phone_number}' must start with '+91'"
    )
    assert len(phone_number) == 13, (
        f"Phone number '{phone_number}' must be 13 characters long (+91 + 10 digits)"
    )
    assert phone_number[3:].isdigit(), (
        f"Phone number '{phone_number}' must contain only digits after '+91'"
    )


def assert_valid_location(location: Dict[str, str]) -> None:
    """Assert that location data is complete and valid."""
    required_fields = {'state', 'city', 'pincode'}
    assert all(field in location for field in required_fields), (
        f"Location must contain all required fields: {required_fields}. "
        f"Got: {set(location.keys())}"
    )
    
    assert len(location['pincode']) == 6, (
        f"Pincode '{location['pincode']}' must be 6 digits long"
    )
    assert location['pincode'].isdigit(), (
        f"Pincode '{location['pincode']}' must contain only digits"
    )


def assert_valid_multilingual_text(text: Dict[str, str]) -> None:
    """Assert that multilingual text contains valid language mappings."""
    assert isinstance(text, dict), "Multilingual text must be a dictionary"
    assert len(text) > 0, "Multilingual text must contain at least one language"
    
    for lang_code, content in text.items():
        assert_valid_language_code(lang_code)
        assert isinstance(content, str), (
            f"Content for language '{lang_code}' must be a string"
        )
        assert len(content.strip()) > 0, (
            f"Content for language '{lang_code}' cannot be empty"
        )


def assert_valid_price(price: Decimal, min_price: Decimal = Decimal('0.01')) -> None:
    """Assert that a price is valid and reasonable."""
    assert isinstance(price, Decimal), f"Price must be a Decimal, got {type(price)}"
    assert price >= min_price, f"Price {price} must be at least {min_price}"
    assert price <= Decimal('100000.00'), f"Price {price} seems unreasonably high"
    
    # Check decimal places (should have at most 2)
    assert price.as_tuple().exponent >= -2, (
        f"Price {price} should have at most 2 decimal places"
    )


def assert_valid_product_data(product: Dict[str, Any]) -> None:
    """Assert that product data is complete and valid."""
    required_fields = {
        'name', 'category', 'description', 'base_price', 
        'unit', 'quality_grade', 'availability'
    }
    
    assert all(field in product for field in required_fields), (
        f"Product must contain all required fields: {required_fields}. "
        f"Got: {set(product.keys())}"
    )
    
    assert_valid_multilingual_text(product['name'])
    assert_valid_multilingual_text(product['description'])
    assert_valid_price(product['base_price'])
    
    valid_categories = {
        'vegetables', 'fruits', 'grains', 'spices', 'dairy'
    }
    assert product['category'] in valid_categories, (
        f"Category '{product['category']}' not in valid categories: {valid_categories}"
    )
    
    valid_quality_grades = {
        'premium', 'standard', 'economy', 'organic', 'export_quality'
    }
    assert product['quality_grade'] in valid_quality_grades, (
        f"Quality grade '{product['quality_grade']}' not in valid grades: {valid_quality_grades}"
    )
    
    valid_availability = {'in_stock', 'out_of_stock', 'limited'}
    assert product['availability'] in valid_availability, (
        f"Availability '{product['availability']}' not in valid options: {valid_availability}"
    )


def assert_valid_user_profile(user: Dict[str, Any]) -> None:
    """Assert that user profile data is complete and valid."""
    required_fields = {
        'phone_number', 'preferred_language', 'location', 'tech_literacy_level'
    }
    
    assert all(field in user for field in required_fields), (
        f"User profile must contain all required fields: {required_fields}. "
        f"Got: {set(user.keys())}"
    )
    
    assert_valid_phone_number(user['phone_number'])
    assert_valid_language_code(user['preferred_language'])
    assert_valid_location(user['location'])
    
    valid_tech_levels = {'low', 'medium', 'high'}
    assert user['tech_literacy_level'] in valid_tech_levels, (
        f"Tech literacy level '{user['tech_literacy_level']}' not in valid levels: {valid_tech_levels}"
    )


def assert_valid_vendor_profile(vendor: Dict[str, Any]) -> None:
    """Assert that vendor profile data is complete and valid."""
    # First check user profile fields
    assert_valid_user_profile(vendor)
    
    # Then check vendor-specific fields
    vendor_fields = {'business_name', 'business_type', 'specializations'}
    assert all(field in vendor for field in vendor_fields), (
        f"Vendor profile must contain vendor-specific fields: {vendor_fields}. "
        f"Got: {set(vendor.keys())}"
    )
    
    assert isinstance(vendor['business_name'], str), "Business name must be a string"
    assert len(vendor['business_name'].strip()) > 0, "Business name cannot be empty"
    
    valid_business_types = {
        'retail', 'wholesale', 'distributor', 'farmer', 'cooperative'
    }
    assert vendor['business_type'] in valid_business_types, (
        f"Business type '{vendor['business_type']}' not in valid types: {valid_business_types}"
    )
    
    assert isinstance(vendor['specializations'], list), "Specializations must be a list"
    assert len(vendor['specializations']) > 0, "Vendor must have at least one specialization"
    
    valid_categories = {
        'vegetables', 'fruits', 'grains', 'spices', 'dairy'
    }
    for specialization in vendor['specializations']:
        assert specialization in valid_categories, (
            f"Specialization '{specialization}' not in valid categories: {valid_categories}"
        )


def assert_translation_quality(
    original: str, 
    translated: str, 
    source_lang: str, 
    target_lang: str,
    min_confidence: float = 0.7
) -> None:
    """Assert that a translation meets quality standards."""
    assert isinstance(original, str), "Original text must be a string"
    assert isinstance(translated, str), "Translated text must be a string"
    assert len(original.strip()) > 0, "Original text cannot be empty"
    assert len(translated.strip()) > 0, "Translated text cannot be empty"
    
    assert_valid_language_code(source_lang)
    assert_valid_language_code(target_lang)
    
    # Basic quality checks
    assert original != translated or source_lang == target_lang, (
        "Translation should differ from original unless same language"
    )
    
    # Length check - translation shouldn't be drastically different in length
    # (allowing for language differences)
    length_ratio = len(translated) / len(original)
    assert 0.3 <= length_ratio <= 3.0, (
        f"Translation length ratio {length_ratio:.2f} seems unreasonable. "
        f"Original: {len(original)} chars, Translated: {len(translated)} chars"
    )


def assert_price_recommendation_quality(
    recommendation: Dict[str, Any],
    product_id: str,
    location: Dict[str, str]
) -> None:
    """Assert that a price recommendation is complete and reasonable."""
    required_fields = {
        'recommended_price', 'confidence_score', 'price_range', 
        'factors_considered', 'data_sources', 'last_updated'
    }
    
    assert all(field in recommendation for field in required_fields), (
        f"Price recommendation must contain all required fields: {required_fields}. "
        f"Got: {set(recommendation.keys())}"
    )
    
    assert_valid_price(recommendation['recommended_price'])
    
    confidence = recommendation['confidence_score']
    assert 0.0 <= confidence <= 1.0, (
        f"Confidence score {confidence} must be between 0.0 and 1.0"
    )
    
    price_range = recommendation['price_range']
    assert 'min' in price_range and 'max' in price_range, (
        "Price range must contain 'min' and 'max' values"
    )
    assert_valid_price(price_range['min'])
    assert_valid_price(price_range['max'])
    assert price_range['min'] <= price_range['max'], (
        f"Price range min ({price_range['min']}) must be <= max ({price_range['max']})"
    )
    
    # Recommended price should be within the range
    rec_price = recommendation['recommended_price']
    assert price_range['min'] <= rec_price <= price_range['max'], (
        f"Recommended price {rec_price} must be within range "
        f"[{price_range['min']}, {price_range['max']}]"
    )


def assert_negotiation_session_valid(session: Dict[str, Any]) -> None:
    """Assert that a negotiation session is properly structured."""
    required_fields = {
        'id', 'buyer_id', 'vendor_id', 'product_id', 'status',
        'current_offer', 'started_at', 'expires_at'
    }
    
    assert all(field in session for field in required_fields), (
        f"Negotiation session must contain all required fields: {required_fields}. "
        f"Got: {set(session.keys())}"
    )
    
    valid_statuses = {
        'active', 'completed', 'expired', 'cancelled', 'pending'
    }
    assert session['status'] in valid_statuses, (
        f"Session status '{session['status']}' not in valid statuses: {valid_statuses}"
    )
    
    if session['current_offer']:
        assert_valid_price(session['current_offer'])
    
    # Time validation
    started_at = session['started_at']
    expires_at = session['expires_at']
    
    if isinstance(started_at, str):
        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    
    assert started_at < expires_at, (
        f"Session start time {started_at} must be before expiry time {expires_at}"
    )


def assert_search_results_valid(
    results: List[Dict[str, Any]], 
    query: str, 
    filters: Optional[Dict[str, Any]] = None
) -> None:
    """Assert that search results are properly formatted and relevant."""
    assert isinstance(results, list), "Search results must be a list"
    
    for result in results:
        required_fields = {
            'id', 'name', 'category', 'price', 'vendor_id', 
            'availability', 'location', 'rating'
        }
        
        assert all(field in result for field in required_fields), (
            f"Search result must contain all required fields: {required_fields}. "
            f"Got: {set(result.keys())}"
        )
        
        assert_valid_multilingual_text(result['name'])
        assert_valid_price(result['price'])
        assert_valid_location(result['location'])
        
        # Check rating
        rating = result['rating']
        assert 0.0 <= rating <= 5.0, f"Rating {rating} must be between 0.0 and 5.0"
    
    # If filters were applied, verify they're respected
    if filters:
        if 'category' in filters:
            for result in results:
                assert result['category'] == filters['category'], (
                    f"Result category '{result['category']}' doesn't match filter '{filters['category']}'"
                )
        
        if 'price_range' in filters:
            price_min = filters['price_range'].get('min')
            price_max = filters['price_range'].get('max')
            
            for result in results:
                if price_min:
                    assert result['price'] >= price_min, (
                        f"Result price {result['price']} below minimum {price_min}"
                    )
                if price_max:
                    assert result['price'] <= price_max, (
                        f"Result price {result['price']} above maximum {price_max}"
                    )


def assert_market_data_fresh(
    data: Dict[str, Any], 
    max_age_minutes: int = 15
) -> None:
    """Assert that market data is fresh and within acceptable age limits."""
    assert 'last_updated' in data, "Market data must include 'last_updated' timestamp"
    
    last_updated = data['last_updated']
    if isinstance(last_updated, str):
        last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
    
    age = datetime.now() - last_updated
    max_age = timedelta(minutes=max_age_minutes)
    
    assert age <= max_age, (
        f"Market data is too old. Age: {age}, Max allowed: {max_age}"
    )


def assert_cultural_adaptation_applied(
    original_message: str,
    adapted_message: str,
    source_profile: Dict[str, Any],
    target_profile: Dict[str, Any]
) -> None:
    """Assert that cultural adaptation has been properly applied to a message."""
    assert isinstance(adapted_message, str), "Adapted message must be a string"
    assert len(adapted_message.strip()) > 0, "Adapted message cannot be empty"
    
    # If profiles are from different regions, adaptation should occur
    source_location = source_profile.get('location', {})
    target_location = target_profile.get('location', {})
    
    if source_location.get('state') != target_location.get('state'):
        # Some adaptation should have occurred
        # This is a basic check - in practice, we'd have more sophisticated validation
        assert adapted_message != original_message or len(adapted_message) != len(original_message), (
            "Cultural adaptation should modify the message for different regions"
        )