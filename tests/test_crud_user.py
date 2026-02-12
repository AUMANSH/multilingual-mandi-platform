"""
Unit tests for User and Vendor CRUD operations.

Tests the database operations for user management including
creation, retrieval, updates, and specialized queries.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from mandi_platform.crud.user import UserCRUD, VendorCRUD, user_crud, vendor_crud
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


class TestUserCRUD:
    """Test cases for UserCRUD operations."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "phone_number": "+919876543210",
            "preferred_language": LanguageCode.HINDI,
            "location": "Mumbai, Maharashtra, India",
            "tech_literacy_level": TechLiteracyLevel.BEGINNER,
            "verification_status": VerificationStatus.UNVERIFIED
        }
    
    @pytest.fixture
    def sample_user(self, sample_user_data):
        """Create a sample user instance."""
        return User(**sample_user_data)
    
    def test_user_crud_initialization(self):
        """Test UserCRUD initialization."""
        crud = UserCRUD(User)
        assert crud.model == User
    
    @pytest.mark.asyncio
    async def test_get_by_phone_found(self, mock_db_session, sample_user):
        """Test getting user by phone number when user exists."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        crud = UserCRUD(User)
        result = await crud.get_by_phone(mock_db_session, "+919876543210")
        
        assert result == sample_user
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_phone_not_found(self, mock_db_session):
        """Test getting user by phone number when user doesn't exist."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        crud = UserCRUD(User)
        result = await crud.get_by_phone(mock_db_session, "+919999999999")
        
        assert result is None
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_language(self, mock_db_session, sample_user):
        """Test getting users by preferred language."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_user]
        mock_db_session.execute.return_value = mock_result
        
        crud = UserCRUD(User)
        result = await crud.get_by_language(mock_db_session, LanguageCode.HINDI)
        
        assert result == [sample_user]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_verification_status(self, mock_db_session, sample_user):
        """Test getting users by verification status."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_user]
        mock_db_session.execute.return_value = mock_result
        
        crud = UserCRUD(User)
        result = await crud.get_by_verification_status(
            mock_db_session, VerificationStatus.UNVERIFIED
        )
        
        assert result == [sample_user]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_by_location(self, mock_db_session, sample_user):
        """Test searching users by location."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_user]
        mock_db_session.execute.return_value = mock_result
        
        crud = UserCRUD(User)
        result = await crud.search_by_location(mock_db_session, "Mumbai")
        
        assert result == [sample_user]
        mock_db_session.execute.assert_called_once()
    
    def test_global_user_crud_instance(self):
        """Test that global user_crud instance is properly initialized."""
        assert isinstance(user_crud, UserCRUD)
        assert user_crud.model == User


class TestVendorCRUD:
    """Test cases for VendorCRUD operations."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_vendor_data(self):
        """Sample vendor data for testing."""
        return {
            "phone_number": "+919876543210",
            "preferred_language": LanguageCode.TAMIL,
            "location": "Chennai, Tamil Nadu, India",
            "tech_literacy_level": TechLiteracyLevel.INTERMEDIATE,
            "verification_status": VerificationStatus.PHONE_VERIFIED,
            "business_name": "Tamil Spices Co.",
            "business_type": BusinessType.SMALL_BUSINESS,
            "rating": Decimal('4.2'),
            "total_transactions": 25,
            "market_reputation": MarketReputation.DEVELOPING
        }
    
    @pytest.fixture
    def sample_vendor(self, sample_vendor_data):
        """Create a sample vendor instance."""
        vendor = Vendor(**sample_vendor_data)
        vendor.id = uuid4()
        return vendor
    
    def test_vendor_crud_initialization(self):
        """Test VendorCRUD initialization."""
        crud = VendorCRUD(Vendor)
        assert crud.model == Vendor
    
    @pytest.mark.asyncio
    async def test_get_by_business_name(self, mock_db_session, sample_vendor):
        """Test getting vendor by business name."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vendor
        mock_db_session.execute.return_value = mock_result
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_by_business_name(mock_db_session, "Tamil Spices Co.")
        
        assert result == sample_vendor
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_business_type(self, mock_db_session, sample_vendor):
        """Test getting vendors by business type."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_vendor]
        mock_db_session.execute.return_value = mock_result
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_by_business_type(
            mock_db_session, BusinessType.SMALL_BUSINESS
        )
        
        assert result == [sample_vendor]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_rating_range(self, mock_db_session, sample_vendor):
        """Test getting vendors by rating range."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_vendor]
        mock_db_session.execute.return_value = mock_result
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_by_rating_range(
            mock_db_session, 
            min_rating=Decimal('4.0'), 
            max_rating=Decimal('5.0')
        )
        
        assert result == [sample_vendor]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_specialization(self, mock_db_session, sample_vendor):
        """Test getting vendors by specialization."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_vendor]
        mock_db_session.execute.return_value = mock_result
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_by_specialization(
            mock_db_session, ProductCategory.SPICES
        )
        
        assert result == [sample_vendor]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_trusted_vendors(self, mock_db_session, sample_vendor):
        """Test getting trusted vendors."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_vendor]
        mock_db_session.execute.return_value = mock_result
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_trusted_vendors(mock_db_session)
        
        assert result == [sample_vendor]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_location_and_category(self, mock_db_session, sample_vendor):
        """Test getting vendors by location and category."""
        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_vendor]
        mock_db_session.execute.return_value = mock_result
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_by_location_and_category(
            mock_db_session, "Chennai", ProductCategory.SPICES
        )
        
        assert result == [sample_vendor]
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_rating(self, mock_db_session, sample_vendor):
        """Test updating vendor rating."""
        # Mock the get method to return the vendor
        crud = VendorCRUD(Vendor)
        crud.get = AsyncMock(return_value=sample_vendor)
        
        original_rating = sample_vendor.rating
        original_transactions = sample_vendor.total_transactions
        
        result = await crud.update_rating(
            mock_db_session, sample_vendor.id, Decimal('5.0'), 2
        )
        
        assert result == sample_vendor
        # Verify rating was updated (weighted average)
        expected_rating = (original_rating * original_transactions + Decimal('5.0') * 2) / (original_transactions + 2)
        assert sample_vendor.rating == expected_rating
        assert sample_vendor.total_transactions == original_transactions + 2
        
        mock_db_session.add.assert_called_once_with(sample_vendor)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(sample_vendor)
    
    @pytest.mark.asyncio
    async def test_add_specialization(self, mock_db_session, sample_vendor):
        """Test adding specialization to vendor."""
        # Mock the get method to return the vendor
        crud = VendorCRUD(Vendor)
        crud.get = AsyncMock(return_value=sample_vendor)
        
        result = await crud.add_specialization(
            mock_db_session, sample_vendor.id, ProductCategory.SPICES
        )
        
        assert result == sample_vendor
        assert ProductCategory.SPICES.value in sample_vendor.specializations
        
        mock_db_session.add.assert_called_once_with(sample_vendor)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(sample_vendor)
    
    @pytest.mark.asyncio
    async def test_add_payment_method(self, mock_db_session, sample_vendor):
        """Test adding payment method to vendor."""
        # Mock the get method to return the vendor
        crud = VendorCRUD(Vendor)
        crud.get = AsyncMock(return_value=sample_vendor)
        
        result = await crud.add_payment_method(
            mock_db_session, sample_vendor.id, PaymentMethod.UPI
        )
        
        assert result == sample_vendor
        assert PaymentMethod.UPI.value in sample_vendor.payment_methods
        
        mock_db_session.add.assert_called_once_with(sample_vendor)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(sample_vendor)
    
    @pytest.mark.asyncio
    async def test_get_vendor_statistics(self, mock_db_session):
        """Test getting vendor statistics."""
        # Mock the database query results
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=lambda: 100),  # total_vendors
            MagicMock(scalar=lambda: Decimal('4.2')),  # avg_rating
            MagicMock(scalar=lambda: 5000),  # total_transactions
            MagicMock(scalar=lambda: 75),  # verified_vendors
            MagicMock(scalar=lambda: 25),  # trusted_vendors
        ]
        
        crud = VendorCRUD(Vendor)
        result = await crud.get_vendor_statistics(mock_db_session)
        
        expected_stats = {
            "total_vendors": 100,
            "average_rating": 4.2,
            "total_transactions": 5000,
            "verified_vendors": 75,
            "trusted_vendors": 25,
        }
        
        assert result == expected_stats
        assert mock_db_session.execute.call_count == 5
    
    def test_global_vendor_crud_instance(self):
        """Test that global vendor_crud instance is properly initialized."""
        assert isinstance(vendor_crud, VendorCRUD)
        assert vendor_crud.model == Vendor


class TestCRUDIntegration:
    """Integration tests for CRUD operations."""
    
    def test_user_and_vendor_crud_instances_different(self):
        """Test that user and vendor CRUD instances are different."""
        assert user_crud != vendor_crud
        assert user_crud.model != vendor_crud.model
        assert user_crud.model == User
        assert vendor_crud.model == Vendor
    
    def test_crud_inheritance(self):
        """Test that CRUD classes properly inherit from base."""
        from mandi_platform.crud.base import CRUDBase
        
        assert issubclass(UserCRUD, CRUDBase)
        assert issubclass(VendorCRUD, CRUDBase)
        
        # Test that they have base methods
        assert hasattr(user_crud, 'get')
        assert hasattr(user_crud, 'create')
        assert hasattr(user_crud, 'update')
        assert hasattr(user_crud, 'remove')
        
        assert hasattr(vendor_crud, 'get')
        assert hasattr(vendor_crud, 'create')
        assert hasattr(vendor_crud, 'update')
        assert hasattr(vendor_crud, 'remove')