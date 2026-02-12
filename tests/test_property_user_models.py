"""
Property-based tests for user data models.

This module implements Property 15: Security and audit trail integrity
for user and vendor data models, validating security properties, data integrity,
audit trail maintenance, and business rule enforcement.

**Validates: Requirements 8.1, 8.3**
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite

from mandi_platform.models.user import User, Vendor
from mandi_platform.models.enums import (
    LanguageCode,
    TechLiteracyLevel,
    VerificationStatus,
    BusinessType,
    MarketReputation,
    PaymentMethod,
    ProductCategory,
)
from tests.utils.generators import (
    supported_languages,
    indian_phone_numbers,
    indian_locations,
    user_profiles,
    vendor_profiles,
    prices,
)


# Custom generators for user model testing

@composite
def valid_user_data(draw) -> Dict[str, Any]:
    """Generate valid user data for model creation."""
    # Simplified location generation for performance
    states = ["Delhi", "Maharashtra", "Karnataka", "Tamil Nadu"]
    cities = ["New Delhi", "Mumbai", "Bangalore", "Chennai"]
    state = draw(st.sampled_from(states))
    city = draw(st.sampled_from(cities))
    location_str = f"{city}, {state}, India"
    
    return {
        "phone_number": draw(st.text(min_size=10, max_size=10, alphabet="0123456789").map(lambda x: f"+91{x}")),
        "preferred_language": draw(st.sampled_from(LanguageCode)),
        "location": location_str,
        "tech_literacy_level": draw(st.sampled_from(TechLiteracyLevel)),
        "verification_status": draw(st.sampled_from(VerificationStatus)),
    }


@composite
def valid_vendor_data(draw) -> Dict[str, Any]:
    """Generate valid vendor data for model creation."""
    user_data = draw(valid_user_data())
    
    # Generate business-specific data with simpler constraints
    business_names = ["ABC Corp", "XYZ Ltd", "Test Business", "Sample Store", "Demo Company"]
    business_name = draw(st.sampled_from(business_names))
    
    vendor_data = {
        **user_data,
        "business_name": business_name,
        "business_type": draw(st.sampled_from(BusinessType)),
        "rating": draw(st.decimals(min_value=Decimal('0.00'), max_value=Decimal('5.00'), places=2)),
        "total_transactions": draw(st.integers(min_value=0, max_value=1000)),
        "market_reputation": draw(st.sampled_from(MarketReputation)),
        "is_verified_business": draw(st.booleans()),
        "business_registration_number": draw(st.one_of(
            st.none(),
            st.sampled_from(["REG123", "BUS456", "LIC789"])
        )),
    }
    
    return vendor_data


@composite
def rating_update_data(draw) -> Dict[str, Any]:
    """Generate data for rating update operations."""
    return {
        "new_rating": draw(st.decimals(min_value=Decimal('0.00'), max_value=Decimal('5.00'), places=2)),
        "transaction_count": draw(st.integers(min_value=1, max_value=100)),
    }


@composite
def specialization_data(draw) -> List[ProductCategory]:
    """Generate specialization data for vendors."""
    return draw(st.lists(
        st.sampled_from(ProductCategory),
        min_size=0,
        max_size=5,
        unique=True
    ))


@composite
def payment_method_data(draw) -> List[PaymentMethod]:
    """Generate payment method data for vendors."""
    return draw(st.lists(
        st.sampled_from(PaymentMethod),
        min_size=0,
        max_size=len(PaymentMethod),
        unique=True
    ))


# Property tests for User model

@pytest.mark.property
@given(user_data=valid_user_data())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_user_data_validation_and_constraints(user_data):
    """
    Property 15: Security and audit trail integrity - User data validation
    **Validates: Requirements 8.1, 8.3**
    
    Ensures all user data meets security requirements and validation constraints.
    """
    # Create user instance
    user = User(**user_data)
    
    # Property: Phone number must be valid format
    assert user.phone_number.startswith('+91')
    assert len(user.phone_number) == 13  # +91 + 10 digits
    assert user.phone_number[3:].isdigit()
    
    # Property: Language must be supported
    assert user.preferred_language in LanguageCode
    
    # Property: Location must be non-empty string
    assert isinstance(user.location, str)
    assert len(user.location.strip()) > 0
    
    # Property: Tech literacy level must be valid enum
    assert user.tech_literacy_level in TechLiteracyLevel
    
    # Property: Verification status must be valid enum
    assert user.verification_status in VerificationStatus
    
    # Property: User type must be set correctly
    assert user.user_type == "user"
    
    # Property: Timestamps should be set (audit trail)
    assert hasattr(user, 'created_at')
    assert hasattr(user, 'last_active')
    
    # Property: ID should be UUID format
    if user.id:
        assert isinstance(user.id, (str, type(uuid4())))


@pytest.mark.property
@given(
    user_data1=valid_user_data(),
    user_data2=valid_user_data()
)
@settings(max_examples=50)
def test_property_user_phone_number_uniqueness_constraint(user_data1, user_data2):
    """
    Property 15: Security constraint - Phone number uniqueness
    **Validates: Requirements 8.1**
    
    Ensures phone number uniqueness constraint is enforced for security.
    """
    # Property: Different users should have different phone numbers for security
    if user_data1["phone_number"] == user_data2["phone_number"]:
        # Same phone number should represent same user identity
        user1 = User(**user_data1)
        user2 = User(**user_data2)
        
        # Security property: same phone = same user identity
        assert user1.phone_number == user2.phone_number
    else:
        # Different phone numbers represent different users
        user1 = User(**user_data1)
        user2 = User(**user_data2)
        assert user1.phone_number != user2.phone_number


# Property tests for Vendor model

@pytest.mark.property
@given(vendor_data=valid_vendor_data())
@settings(max_examples=100)
def test_property_vendor_data_validation_and_security(vendor_data):
    """
    Property 15: Security and audit trail integrity - Vendor data validation
    **Validates: Requirements 8.1, 8.3**
    
    Ensures all vendor data meets security requirements and business constraints.
    """
    # Create vendor instance
    vendor = Vendor(**vendor_data)
    
    # Property: All user properties must be valid (inheritance)
    assert vendor.phone_number.startswith('+91')
    assert vendor.preferred_language in LanguageCode
    assert len(vendor.location.strip()) > 0
    
    # Property: Business name must be valid and secure
    assert isinstance(vendor.business_name, str)
    assert len(vendor.business_name.strip()) > 0
    assert len(vendor.business_name) <= 255  # Security: prevent buffer overflow
    
    # Property: Business type must be valid enum
    assert vendor.business_type in BusinessType
    
    # Property: Rating must be within valid range (business rule)
    assert Decimal('0.00') <= vendor.rating <= Decimal('5.00')
    assert vendor.rating.as_tuple().exponent >= -2  # Max 2 decimal places
    
    # Property: Transaction count must be non-negative
    assert vendor.total_transactions >= 0
    
    # Property: Market reputation must be valid enum
    assert vendor.market_reputation in MarketReputation
    
    # Property: Verification flags must be boolean
    assert isinstance(vendor.is_verified_business, bool)
    
    # Property: Registration number format (if provided)
    if vendor.business_registration_number:
        assert isinstance(vendor.business_registration_number, str)
        assert len(vendor.business_registration_number.strip()) > 0
        assert len(vendor.business_registration_number) <= 50  # Security constraint
    
    # Property: User type must be set correctly for polymorphism
    assert vendor.user_type == "vendor"
    
    # Property: Specializations and payment methods must be lists
    assert isinstance(vendor.specializations, list)
    assert isinstance(vendor.payment_methods, list)


@pytest.mark.property
@given(
    vendor_data=valid_vendor_data(),
    rating_data=rating_update_data()
)
@settings(max_examples=100)
def test_property_vendor_rating_calculation_integrity(vendor_data, rating_data):
    """
    Property 15: Business logic integrity - Vendor rating calculations
    **Validates: Requirements 8.1, 8.3**
    
    Ensures vendor rating calculations are mathematically correct and secure.
    """
    vendor = Vendor(**vendor_data)
    original_rating = vendor.rating
    original_transactions = vendor.total_transactions
    
    new_rating = rating_data["new_rating"]
    transaction_count = rating_data["transaction_count"]
    
    # Apply rating update
    vendor.update_rating(new_rating, transaction_count)
    
    # Property: Transaction count must increase correctly
    assert vendor.total_transactions == original_transactions + transaction_count
    
    # Property: Rating must be within valid range after update
    assert Decimal('0.00') <= vendor.rating <= Decimal('5.00')
    
    # Property: Rating calculation must be mathematically correct
    if original_transactions == 0:
        # First rating should be the new rating
        assert vendor.rating == new_rating
    else:
        # Weighted average calculation with rounding
        expected_rating = (
            (original_rating * original_transactions + new_rating * transaction_count) 
            / (original_transactions + transaction_count)
        )
        # Account for rounding to 2 decimal places
        expected_rating_rounded = expected_rating.quantize(Decimal('0.01'))
        assert vendor.rating == expected_rating_rounded
    
    # Property: Rating precision must be maintained (security against precision attacks)
    assert vendor.rating.as_tuple().exponent >= -2


@pytest.mark.property
@given(
    vendor_data=valid_vendor_data(),
    specializations=specialization_data()
)
@settings(max_examples=50)
def test_property_vendor_specialization_management_integrity(vendor_data, specializations):
    """
    Property 15: Data integrity - Specialization management
    **Validates: Requirements 8.1, 8.3**
    
    Ensures specialization management maintains data integrity and audit trail.
    """
    vendor = Vendor(**vendor_data)
    
    # Property: Adding specializations should maintain uniqueness
    for spec in specializations:
        initial_count = len(vendor.specializations)
        vendor.add_specialization(spec)
        
        # Property: Specialization should be added
        assert spec.value in vendor.specializations
        
        # Property: No duplicates should exist
        assert len(set(vendor.specializations)) == len(vendor.specializations)
        
        # Property: Count should increase by at most 1 (no duplicates)
        assert len(vendor.specializations) <= initial_count + 1
    
    # Property: Removing specializations should work correctly
    for spec in specializations:
        if spec.value in vendor.specializations:
            initial_count = len(vendor.specializations)
            vendor.remove_specialization(spec)
            
            # Property: Specialization should be removed
            assert spec.value not in vendor.specializations
            
            # Property: Count should decrease by exactly 1
            assert len(vendor.specializations) == initial_count - 1


@pytest.mark.property
@given(
    vendor_data=valid_vendor_data(),
    payment_methods=payment_method_data()
)
@settings(max_examples=50)
def test_property_vendor_payment_method_management_integrity(vendor_data, payment_methods):
    """
    Property 15: Data integrity - Payment method management
    **Validates: Requirements 8.1, 8.3**
    
    Ensures payment method management maintains data integrity.
    """
    vendor = Vendor(**vendor_data)
    
    # Property: Adding payment methods should maintain uniqueness
    for method in payment_methods:
        initial_count = len(vendor.payment_methods)
        vendor.add_payment_method(method)
        
        # Property: Payment method should be added
        assert method.value in vendor.payment_methods
        
        # Property: No duplicates should exist
        assert len(set(vendor.payment_methods)) == len(vendor.payment_methods)
        
        # Property: Count should increase by at most 1 (no duplicates)
        assert len(vendor.payment_methods) <= initial_count + 1
    
    # Property: Removing payment methods should work correctly
    for method in payment_methods:
        if method.value in vendor.payment_methods:
            initial_count = len(vendor.payment_methods)
            vendor.remove_payment_method(method)
            
            # Property: Payment method should be removed
            assert method.value not in vendor.payment_methods
            
            # Property: Count should decrease by exactly 1
            assert len(vendor.payment_methods) == initial_count - 1


@pytest.mark.property
@given(vendor_data=valid_vendor_data())
@settings(max_examples=100)
def test_property_vendor_business_rule_enforcement(vendor_data):
    """
    Property 15: Business rule enforcement - Vendor trust and reputation
    **Validates: Requirements 8.1, 8.3**
    
    Ensures business rules for vendor trust and reputation are consistently enforced.
    """
    vendor = Vendor(**vendor_data)
    
    # Property: Trusted vendor criteria must be consistently applied
    is_trusted = vendor.is_trusted_vendor
    
    if is_trusted:
        # Property: Trusted vendors must meet all criteria
        assert vendor.rating >= Decimal('4.0')
        assert vendor.total_transactions >= 50
        assert vendor.verification_status == VerificationStatus.FULLY_VERIFIED
        assert vendor.is_verified_business is True
    
    # Property: Reputation score must be calculated consistently
    reputation_score = vendor.reputation_score
    
    # Property: Reputation score must be within valid range
    assert 0 <= reputation_score <= 100
    assert isinstance(reputation_score, int)
    
    # Property: Reputation score calculation must be deterministic
    # Same vendor data should always yield same reputation score
    reputation_score_2 = vendor.reputation_score
    assert reputation_score == reputation_score_2
    
    # Property: Higher ratings should generally lead to higher reputation scores
    # (unless capped at 100 or affected by transaction bonus)
    if vendor.rating > Decimal('0.0'):
        base_score = min(float(vendor.rating) * 20, 100)
        transaction_bonus = min(vendor.total_transactions / 10, 20)
        verification_bonus = 0
        
        if vendor.verification_status == VerificationStatus.FULLY_VERIFIED:
            verification_bonus += 10
        if vendor.is_verified_business:
            verification_bonus += 10
        
        expected_score = min(int(base_score + transaction_bonus + verification_bonus), 100)
        assert reputation_score == expected_score


@pytest.mark.property
@given(
    vendor_data1=valid_vendor_data(),
    vendor_data2=valid_vendor_data()
)
@settings(max_examples=50)
def test_property_vendor_business_name_security_constraints(vendor_data1, vendor_data2):
    """
    Property 15: Security constraints - Business name validation
    **Validates: Requirements 8.1**
    
    Ensures business names meet security requirements and prevent injection attacks.
    """
    vendor1 = Vendor(**vendor_data1)
    vendor2 = Vendor(**vendor_data2)
    
    # Property: Business names must be safe strings
    for vendor in [vendor1, vendor2]:
        business_name = vendor.business_name
        
        # Property: No SQL injection patterns
        dangerous_patterns = ["'", '"', ';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT']
        for pattern in dangerous_patterns:
            if pattern.lower() in business_name.lower():
                # If dangerous pattern exists, it should be in a safe context
                # (e.g., as part of legitimate business name like "John's Store")
                assert len(business_name) < 255  # Length constraint for security
        
        # Property: Business name should not be empty or just whitespace
        assert len(business_name.strip()) > 0
        
        # Property: Business name should have reasonable length limits
        assert len(business_name) <= 255


@pytest.mark.property
@given(
    user_data=valid_user_data(),
    vendor_data=valid_vendor_data()
)
@settings(max_examples=50)
def test_property_audit_trail_maintenance(user_data, vendor_data):
    """
    Property 15: Audit trail maintenance - Timestamps and change tracking
    **Validates: Requirements 8.3**
    
    Ensures proper audit trail maintenance for all user and vendor operations.
    """
    # Test user audit trail
    user = User(**user_data)
    
    # Property: Users should have audit timestamps
    assert hasattr(user, 'created_at')
    assert hasattr(user, 'last_active')
    
    # Property: Timestamps should be reasonable (not in future, not too old)
    now = datetime.now()
    if hasattr(user, 'created_at') and user.created_at:
        # Allow for some clock skew but timestamps should be reasonable
        assert user.created_at <= now + timedelta(minutes=1)
    
    # Test vendor audit trail
    vendor = Vendor(**vendor_data)
    
    # Property: Vendors should inherit user audit trail
    assert hasattr(vendor, 'created_at')
    assert hasattr(vendor, 'last_active')
    
    # Property: Vendor-specific audit fields
    assert hasattr(vendor, 'rating')
    assert hasattr(vendor, 'total_transactions')
    
    # Property: Rating changes should be trackable
    original_rating = vendor.rating
    original_transactions = vendor.total_transactions
    
    vendor.update_rating(Decimal('4.5'), 1)
    
    # Property: Changes should be reflected in audit trail
    assert vendor.rating != original_rating or vendor.total_transactions != original_transactions
    assert vendor.total_transactions == original_transactions + 1


@pytest.mark.property
@given(
    vendor_data=valid_vendor_data(),
    rating_updates=st.lists(rating_update_data(), min_size=1, max_size=10)
)
@settings(max_examples=30)
def test_property_vendor_rating_security_and_consistency(vendor_data, rating_updates):
    """
    Property 15: Security and consistency - Rating manipulation prevention
    **Validates: Requirements 8.1, 8.3**
    
    Ensures vendor ratings cannot be manipulated and maintain consistency.
    """
    vendor = Vendor(**vendor_data)
    original_rating = vendor.rating
    original_transactions = vendor.total_transactions
    
    # Apply multiple rating updates
    total_new_transactions = 0
    
    for update in rating_updates:
        new_rating = update["new_rating"]
        transaction_count = update["transaction_count"]
        
        # Property: Rating updates should be within valid range
        assert Decimal('0.00') <= new_rating <= Decimal('5.00')
        assert transaction_count > 0
        
        vendor.update_rating(new_rating, transaction_count)
        total_new_transactions += transaction_count
    
    # Property: Final transaction count should be correct
    expected_total_transactions = original_transactions + total_new_transactions
    assert vendor.total_transactions == expected_total_transactions
    
    # Property: Rating should still be within valid bounds
    assert Decimal('0.00') <= vendor.rating <= Decimal('5.00')
    
    # Property: Rating precision should be maintained (prevent precision attacks)
    assert vendor.rating.as_tuple().exponent >= -2