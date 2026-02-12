"""
Test configuration validation.

This module tests that the testing framework configuration is correct
and all required components are available.
"""

import pytest
import sys
import os
from pathlib import Path


@pytest.mark.unit
def test_python_version():
    """Test that we're running on a supported Python version."""
    assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version_info}"


@pytest.mark.unit
def test_required_packages_available():
    """Test that all required testing packages are available."""
    try:
        import pytest
        import hypothesis
        import coverage
        import factory  # factory_boy is imported as 'factory'
        import faker
    except ImportError as e:
        pytest.fail(f"Required testing package not available: {e}")


@pytest.mark.unit
def test_test_directory_structure():
    """Test that the test directory structure is correct."""
    test_dir = Path(__file__).parent
    
    # Check required directories exist
    assert (test_dir / "utils").exists(), "tests/utils directory missing"
    
    # Check required files exist
    required_files = [
        "conftest.py",
        "utils/__init__.py",
        "utils/generators.py",
        "utils/assertions.py",
        "utils/simple_factories.py",
    ]
    
    for file_path in required_files:
        full_path = test_dir / file_path
        assert full_path.exists(), f"Required test file missing: {file_path}"


@pytest.mark.unit
def test_hypothesis_configuration():
    """Test that Hypothesis is configured correctly."""
    from hypothesis import settings, Verbosity
    
    # Test default settings
    default_settings = settings()
    assert default_settings.max_examples >= 100, "Hypothesis max_examples should be at least 100"
    
    # Test custom settings
    custom_settings = settings(max_examples=50, verbosity=Verbosity.verbose)
    assert custom_settings.max_examples == 50
    assert custom_settings.verbosity == Verbosity.verbose


@pytest.mark.unit
def test_pytest_markers():
    """Test that pytest markers are configured correctly."""
    # This test ensures our custom markers are recognized
    import pytest
    
    # These should not raise warnings about unknown markers
    pytest.mark.unit
    pytest.mark.integration
    pytest.mark.property
    pytest.mark.slow


@pytest.mark.unit
def test_test_data_generators():
    """Test that test data generators are working."""
    from tests.utils.generators import (
        supported_languages,
        indian_phone_numbers,
        prices,
    )
    from hypothesis import given, settings
    
    # Test that generators can be used
    @given(lang=supported_languages())
    @settings(max_examples=5)
    def _test_lang_generator(lang):
        assert isinstance(lang, str)
        assert len(lang) == 2
    
    @given(phone=indian_phone_numbers())
    @settings(max_examples=5)
    def _test_phone_generator(phone):
        assert phone.startswith('+91')
        assert len(phone) == 13
    
    @given(price=prices())
    @settings(max_examples=5)
    def _test_price_generator(price):
        from decimal import Decimal
        assert isinstance(price, Decimal)
        assert price > 0
    
    # Run the nested tests
    _test_lang_generator()
    _test_phone_generator()
    _test_price_generator()


@pytest.mark.unit
def test_assertion_helpers():
    """Test that assertion helpers are working."""
    from tests.utils.assertions import (
        assert_valid_language_code,
        assert_valid_phone_number,
        assert_valid_price,
    )
    from decimal import Decimal
    
    # Test valid cases
    assert_valid_language_code('en')
    assert_valid_phone_number('+919876543210')
    assert_valid_price(Decimal('10.50'))
    
    # Test invalid cases raise assertions
    with pytest.raises(AssertionError):
        assert_valid_language_code('invalid')
    
    with pytest.raises(AssertionError):
        assert_valid_phone_number('invalid')
    
    with pytest.raises(AssertionError):
        assert_valid_price(Decimal('-1.00'))


@pytest.mark.integration
def test_full_testing_workflow():
    """Integration test for the complete testing workflow."""
    from tests.utils.simple_factories import create_user_data
    from tests.utils.assertions import assert_valid_user_profile
    from tests.utils.generators import user_profiles
    from hypothesis import given, settings
    
    # Test factory-based data creation
    user_data = create_user_data()
    assert_valid_user_profile(user_data)
    
    # Test property-based data creation
    @given(user=user_profiles())
    @settings(max_examples=5)
    def _test_property_user(user):
        assert_valid_user_profile(user)
    
    _test_property_user()


@pytest.mark.unit
def test_environment_variables():
    """Test that test environment variables are handled correctly."""
    # Test that we can set test-specific environment variables
    os.environ['TEST_MODE'] = 'true'
    assert os.environ.get('TEST_MODE') == 'true'
    
    # Clean up
    del os.environ['TEST_MODE']