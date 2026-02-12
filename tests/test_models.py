"""
Unit tests for User and Vendor models.

Tests the core functionality of the data models including
validation, relationships, and business logic.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

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


class TestUser:
    """Test cases for User model."""
    
    def test_user_creation(self):
        """Test basic user creation with required fields."""
        user = User(
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED
        )
        
        assert user.phone_number == "+919876543210"
        assert user.preferred_language == LanguageCode.HINDI
        assert user.location == "Mumbai, Maharashtra, India"
        assert user.tech_literacy_level == TechLiteracyLevel.BEGINNER
        assert user.verification_status == VerificationStatus.UNVERIFIED
        assert user.user_type == "user"
    
    def test_user_defaults(self):
        """Test that user model has correct default values."""
        user = User(
            phone_number="+919876543210",
            location="Delhi, India"
        )
        
        assert user.preferred_language == LanguageCode.HINDI
        assert user.tech_literacy_level == TechLiteracyLevel.BEGINNER
        assert user.verification_status == VerificationStatus.UNVERIFIED
        assert user.user_type == "user"
    
    def test_user_repr(self):
        """Test user string representation."""
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.ENGLISH,
            location="Chennai, Tamil Nadu, India"
        )
        
        repr_str = repr(user)
        assert "User(" in repr_str
        assert str(user.id) in repr_str
        assert "+919876543210" in repr_str
        assert "ENGLISH" in repr_str


class TestVendor:
    """Test cases for Vendor model."""
    
    def test_vendor_creation(self):
        """Test basic vendor creation with required fields."""
        vendor = Vendor(
            phone_number="+919876543210",
            preferred_language=LanguageCode.TAMIL,
            location="Chennai, Tamil Nadu, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            business_name="Tamil Spices Co.",
            business_type=BusinessType.SMALL_BUSINESS
        )
        
        assert vendor.phone_number == "+919876543210"
        assert vendor.business_name == "Tamil Spices Co."
        assert vendor.business_type == BusinessType.SMALL_BUSINESS
        assert vendor.rating == Decimal('0.00')
        assert vendor.total_transactions == 0
        assert vendor.market_reputation == MarketReputation.NEW
        assert vendor.is_verified_business is False
        assert vendor.user_type == "vendor"
    
    def test_vendor_defaults(self):
        """Test that vendor model has correct default values."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Bangalore, Karnataka, India",
            business_name="Karnataka Textiles",
            business_type=BusinessType.RETAILER
        )
        
        assert vendor.rating == Decimal('0.00')
        assert vendor.total_transactions == 0
        assert vendor.market_reputation == MarketReputation.NEW
        assert vendor.is_verified_business is False
        assert vendor.specializations == []
        assert vendor.payment_methods == []
    
    def test_vendor_repr(self):
        """Test vendor string representation."""
        vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543210",
            location="Pune, Maharashtra, India",
            business_name="Maharashtra Farmers Co-op",
            business_type=BusinessType.COOPERATIVE,
            rating=Decimal('4.25')
        )
        
        repr_str = repr(vendor)
        assert "Vendor(" in repr_str
        assert str(vendor.id) in repr_str
        assert "Maharashtra Farmers Co-op" in repr_str
        assert "4.25" in repr_str
    
    def test_update_rating_first_rating(self):
        """Test updating rating when vendor has no previous transactions."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Kolkata, West Bengal, India",
            business_name="Bengal Sweets",
            business_type=BusinessType.INDIVIDUAL_TRADER
        )
        
        vendor.update_rating(Decimal('4.5'), 1)
        
        assert vendor.rating == Decimal('4.5')
        assert vendor.total_transactions == 1
    
    def test_update_rating_weighted_average(self):
        """Test updating rating with weighted average calculation."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Jaipur, Rajasthan, India",
            business_name="Rajasthani Handicrafts",
            business_type=BusinessType.MANUFACTURER,
            rating=Decimal('4.0'),
            total_transactions=10
        )
        
        # Add 5 transactions with rating 5.0
        vendor.update_rating(Decimal('5.0'), 5)
        
        # Expected: (4.0 * 10 + 5.0 * 5) / 15 = 65/15 = 4.33...
        expected_rating = (Decimal('4.0') * 10 + Decimal('5.0') * 5) / 15
        assert vendor.rating == expected_rating
        assert vendor.total_transactions == 15
    
    def test_specialization_management(self):
        """Test adding and removing specializations."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Hyderabad, Telangana, India",
            business_name="Telangana Spices",
            business_type=BusinessType.WHOLESALER
        )
        
        # Add specializations
        vendor.add_specialization(ProductCategory.SPICES)
        vendor.add_specialization(ProductCategory.GRAINS)
        
        assert ProductCategory.SPICES.value in vendor.specializations
        assert ProductCategory.GRAINS.value in vendor.specializations
        assert len(vendor.specializations) == 2
        
        # Try to add duplicate - should not increase count
        vendor.add_specialization(ProductCategory.SPICES)
        assert len(vendor.specializations) == 2
        
        # Remove specialization
        vendor.remove_specialization(ProductCategory.SPICES)
        assert ProductCategory.SPICES.value not in vendor.specializations
        assert ProductCategory.GRAINS.value in vendor.specializations
        assert len(vendor.specializations) == 1
    
    def test_payment_method_management(self):
        """Test adding and removing payment methods."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Ahmedabad, Gujarat, India",
            business_name="Gujarat Textiles",
            business_type=BusinessType.MANUFACTURER
        )
        
        # Add payment methods
        vendor.add_payment_method(PaymentMethod.UPI)
        vendor.add_payment_method(PaymentMethod.CASH)
        vendor.add_payment_method(PaymentMethod.BANK_TRANSFER)
        
        assert PaymentMethod.UPI.value in vendor.payment_methods
        assert PaymentMethod.CASH.value in vendor.payment_methods
        assert PaymentMethod.BANK_TRANSFER.value in vendor.payment_methods
        assert len(vendor.payment_methods) == 3
        
        # Try to add duplicate - should not increase count
        vendor.add_payment_method(PaymentMethod.UPI)
        assert len(vendor.payment_methods) == 3
        
        # Remove payment method
        vendor.remove_payment_method(PaymentMethod.CASH)
        assert PaymentMethod.CASH.value not in vendor.payment_methods
        assert PaymentMethod.UPI.value in vendor.payment_methods
        assert len(vendor.payment_methods) == 2
    
    def test_get_specializations(self):
        """Test getting specializations as enum objects."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Kochi, Kerala, India",
            business_name="Kerala Spices Export",
            business_type=BusinessType.WHOLESALER
        )
        
        vendor.add_specialization(ProductCategory.SPICES)
        vendor.add_specialization(ProductCategory.SEAFOOD)
        
        specializations = vendor.get_specializations()
        assert ProductCategory.SPICES in specializations
        assert ProductCategory.SEAFOOD in specializations
        assert len(specializations) == 2
        assert all(isinstance(spec, ProductCategory) for spec in specializations)
    
    def test_get_payment_methods(self):
        """Test getting payment methods as enum objects."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Chandigarh, Punjab, India",
            business_name="Punjab Grains",
            business_type=BusinessType.FARMER
        )
        
        vendor.add_payment_method(PaymentMethod.UPI)
        vendor.add_payment_method(PaymentMethod.DIGITAL_WALLET)
        
        payment_methods = vendor.get_payment_methods()
        assert PaymentMethod.UPI in payment_methods
        assert PaymentMethod.DIGITAL_WALLET in payment_methods
        assert len(payment_methods) == 2
        assert all(isinstance(method, PaymentMethod) for method in payment_methods)
    
    def test_is_trusted_vendor_false(self):
        """Test trusted vendor check returns False for new vendor."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Bhopal, Madhya Pradesh, India",
            business_name="MP Handicrafts",
            business_type=BusinessType.INDIVIDUAL_TRADER
        )
        
        assert vendor.is_trusted_vendor is False
    
    def test_is_trusted_vendor_true(self):
        """Test trusted vendor check returns True for qualified vendor."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Lucknow, Uttar Pradesh, India",
            business_name="UP Textiles Ltd",
            business_type=BusinessType.MANUFACTURER,
            rating=Decimal('4.5'),
            total_transactions=100,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            is_verified_business=True
        )
        
        assert vendor.is_trusted_vendor is True
    
    def test_reputation_score_calculation(self):
        """Test reputation score calculation."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Guwahati, Assam, India",
            business_name="Assam Tea Co.",
            business_type=BusinessType.COOPERATIVE,
            rating=Decimal('4.0'),
            total_transactions=50,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            is_verified_business=True
        )
        
        # Expected: 4.0 * 20 + min(50/10, 20) + 10 + 10 = 80 + 20 + 20 = 120, capped at 100
        score = vendor.reputation_score
        assert score == 100
    
    def test_reputation_score_low_rating(self):
        """Test reputation score with low rating."""
        vendor = Vendor(
            phone_number="+919876543210",
            location="Shimla, Himachal Pradesh, India",
            business_name="Himachal Apples",
            business_type=BusinessType.FARMER,
            rating=Decimal('2.5'),
            total_transactions=10,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            is_verified_business=False
        )
        
        # Expected: 2.5 * 20 + min(10/10, 20) + 0 + 0 = 50 + 1 + 0 = 51
        score = vendor.reputation_score
        assert score == 51


class TestEnums:
    """Test cases for enum values."""
    
    def test_language_codes(self):
        """Test that all expected language codes are present."""
        expected_languages = {
            "hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"
        }
        actual_languages = {lang.value for lang in LanguageCode}
        assert actual_languages == expected_languages
    
    def test_business_types(self):
        """Test that all expected business types are present."""
        expected_types = {
            "individual_trader", "small_business", "cooperative", 
            "wholesaler", "retailer", "farmer", "manufacturer"
        }
        actual_types = {bt.value for bt in BusinessType}
        assert actual_types == expected_types
    
    def test_product_categories(self):
        """Test that key product categories are present."""
        key_categories = {
            ProductCategory.GRAINS, ProductCategory.VEGETABLES, 
            ProductCategory.FRUITS, ProductCategory.SPICES
        }
        for category in key_categories:
            assert category in ProductCategory
    
    def test_payment_methods(self):
        """Test that key payment methods are present."""
        key_methods = {
            PaymentMethod.CASH, PaymentMethod.UPI, 
            PaymentMethod.BANK_TRANSFER, PaymentMethod.DIGITAL_WALLET
        }
        for method in key_methods:
            assert method in PaymentMethod