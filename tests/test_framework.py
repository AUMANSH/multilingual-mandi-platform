"""
Basic tests to verify the testing framework is working correctly.

These tests validate that pytest, hypothesis, and our custom generators
are functioning properly without requiring the full application setup.
"""

import pytest
from decimal import Decimal
from hypothesis import given, strategies as st, settings

from tests.utils.generators import (
    supported_languages,
    indian_phone_numbers,
    indian_locations,
    prices,
    user_profiles,
    product_data,
)
from tests.utils.assertions import (
    assert_valid_language_code,
    assert_valid_phone_number,
    assert_valid_location,
    assert_valid_price,
    assert_valid_user_profile,
    assert_valid_product_data,
)


@pytest.mark.unit
def test_basic_pytest_functionality():
    """Test that pytest is working correctly."""
    assert True
    assert 1 + 1 == 2
    assert "hello" == "hello"


@pytest.mark.unit
def test_decimal_arithmetic():
    """Test decimal arithmetic for price calculations."""
    price1 = Decimal('10.50')
    price2 = Decimal('5.25')
    
    total = price1 + price2
    assert total == Decimal('15.75')
    
    # Test precision
    assert total.as_tuple().exponent == -2


@pytest.mark.property
@given(language_code=supported_languages())
@settings(max_examples=20)
def test_property_language_codes_valid(language_code):
    """Property test: All generated language codes should be valid."""
    assert_valid_language_code(language_code)
    assert isinstance(language_code, str)
    assert len(language_code) == 2


@pytest.mark.property
@given(phone_number=indian_phone_numbers())
@settings(max_examples=20)
def test_property_phone_numbers_valid(phone_number):
    """Property test: All generated phone numbers should be valid."""
    assert_valid_phone_number(phone_number)
    assert phone_number.startswith('+91')
    assert len(phone_number) == 13


@pytest.mark.property
@given(location=indian_locations())
@settings(max_examples=20)
def test_property_locations_valid(location):
    """Property test: All generated locations should be valid."""
    assert_valid_location(location)
    assert 'state' in location
    assert 'city' in location
    assert 'pincode' in location


@pytest.mark.property
@given(price=prices())
@settings(max_examples=20)
def test_property_prices_valid(price):
    """Property test: All generated prices should be valid."""
    assert_valid_price(price)
    assert isinstance(price, Decimal)
    assert price > Decimal('0')


@pytest.mark.property
@given(user=user_profiles())
@settings(max_examples=20)
def test_property_user_profiles_valid(user):
    """Property test: All generated user profiles should be valid."""
    assert_valid_user_profile(user)
    assert 'phone_number' in user
    assert 'preferred_language' in user
    assert 'location' in user
    assert 'tech_literacy_level' in user


@pytest.mark.property
@given(product=product_data())
@settings(max_examples=20)
def test_property_product_data_valid(product):
    """Property test: All generated product data should be valid."""
    assert_valid_product_data(product)
    assert 'name' in product
    assert 'category' in product
    assert 'base_price' in product


@pytest.mark.unit
def test_hypothesis_configuration():
    """Test that Hypothesis is configured correctly."""
    from hypothesis import settings
    
    # Test that we can create a settings object
    test_settings = settings(max_examples=10)
    assert test_settings.max_examples == 10


@pytest.mark.unit
def test_test_utilities_import():
    """Test that our test utilities can be imported."""
    from tests.utils.generators import SUPPORTED_LANGUAGES
    from tests.utils.assertions import assert_valid_language_code
    from tests.utils.simple_factories import create_user_data
    
    assert len(SUPPORTED_LANGUAGES) == 10
    assert callable(assert_valid_language_code)
    assert callable(create_user_data)


@pytest.mark.integration
def test_end_to_end_data_generation():
    """Integration test: Generate and validate complete test scenario."""
    from tests.utils.simple_factories import create_negotiation_scenario
    
    scenario = create_negotiation_scenario()
    
    assert 'buyer' in scenario
    assert 'vendor' in scenario
    assert 'product' in scenario
    assert 'offer' in scenario
    
    # Validate each component
    assert_valid_user_profile(scenario['buyer'])
    assert_valid_user_profile(scenario['vendor'])  # Vendor extends user
    assert_valid_product_data(scenario['product'])


@pytest.mark.unit
def test_coverage_reporting():
    """Test that coverage reporting is working."""
    # This test ensures coverage tools can track execution
    def dummy_function(x):
        if x > 0:
            return x * 2
        else:
            return 0
    
    assert dummy_function(5) == 10
    assert dummy_function(-1) == 0
    assert dummy_function(0) == 0