"""
Unit tests for authentication dependencies.

This module tests the FastAPI dependencies for authentication and authorization.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException, status

from src.mandi_platform.auth.dependencies import (
    require_auth,
    require_vendor_auth,
    optional_auth,
    require_verified_user,
    require_verified_vendor,
    require_trusted_vendor,
    RoleChecker,
    require_user_role,
    require_vendor_role,
    require_any_role,
)
from src.mandi_platform.models.user import User, Vendor
from src.mandi_platform.models.enums import (
    LanguageCode,
    TechLiteracyLevel,
    VerificationStatus,
    BusinessType,
    MarketReputation
)
from decimal import Decimal


class TestBasicAuthDependencies:
    """Test basic authentication dependencies."""
    
    def test_require_auth_success(self, test_user: User):
        """Test require_auth with valid user."""
        result = require_auth(test_user)
        assert result == test_user
    
    def test_require_vendor_auth_success(self, test_vendor: Vendor):
        """Test require_vendor_auth with valid vendor."""
        result = require_vendor_auth(test_vendor)
        assert result == test_vendor
    
    def test_optional_auth_with_user(self, test_user: User):
        """Test optional_auth with authenticated user."""
        result = optional_auth(test_user)
        assert result == test_user
    
    def test_optional_auth_without_user(self):
        """Test optional_auth without authenticated user."""
        result = optional_auth(None)
        assert result is None


class TestVerificationDependencies:
    """Test verification-based dependencies."""
    
    def test_require_verified_user_success(self, test_user: User):
        """Test require_verified_user with verified user."""
        test_user.verification_status = VerificationStatus.PHONE_VERIFIED
        result = require_verified_user(test_user)
        assert result == test_user
    
    def test_require_verified_user_unverified(self, test_user: User):
        """Test require_verified_user with unverified user."""
        test_user.verification_status = VerificationStatus.UNVERIFIED
        
        with pytest.raises(HTTPException) as exc_info:
            require_verified_user(test_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "verification required" in exc_info.value.detail.lower()
    
    def test_require_verified_vendor_success(self, test_vendor: Vendor):
        """Test require_verified_vendor with verified vendor."""
        test_vendor.verification_status = VerificationStatus.FULLY_VERIFIED
        result = require_verified_vendor(test_vendor)
        assert result == test_vendor
    
    def test_require_verified_vendor_unverified(self, test_vendor: Vendor):
        """Test require_verified_vendor with unverified vendor."""
        test_vendor.verification_status = VerificationStatus.UNVERIFIED
        
        with pytest.raises(HTTPException) as exc_info:
            require_verified_vendor(test_vendor)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "verification required" in exc_info.value.detail.lower()
    
    def test_require_trusted_vendor_success(self):
        """Test require_trusted_vendor with trusted vendor."""
        trusted_vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.ADVANCED,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="vendor",
            business_name="Trusted Vendor Business",
            business_type=BusinessType.WHOLESALER,
            rating=Decimal('4.5'),
            total_transactions=100,
            is_verified_business=True
        )
        
        result = require_trusted_vendor(trusted_vendor)
        assert result == trusted_vendor
    
    def test_require_trusted_vendor_not_trusted(self, test_vendor: Vendor):
        """Test require_trusted_vendor with non-trusted vendor."""
        # Ensure vendor is not trusted by setting values that don't meet criteria
        test_vendor.rating = Decimal('3.0')  # Below 4.0 threshold
        test_vendor.total_transactions = 10  # Below 50 threshold
        test_vendor.verification_status = VerificationStatus.PHONE_VERIFIED  # Not FULLY_VERIFIED
        test_vendor.is_verified_business = False
        
        with pytest.raises(HTTPException) as exc_info:
            require_trusted_vendor(test_vendor)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "trusted vendor status required" in exc_info.value.detail.lower()


class TestRoleChecker:
    """Test role-based access control checker."""
    
    def test_role_checker_single_role_success(self, test_user: User):
        """Test RoleChecker with single allowed role - success."""
        # Ensure user has the correct user_type
        test_user.user_type = "user"
        checker = RoleChecker(["user"])
        result = checker(test_user)
        assert result == test_user
    
    def test_role_checker_single_role_failure(self, test_vendor: Vendor):
        """Test RoleChecker with single allowed role - failure."""
        checker = RoleChecker(["user"])  # Only allow users
        
        with pytest.raises(HTTPException) as exc_info:
            checker(test_vendor)  # But vendor is provided
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "access denied" in exc_info.value.detail.lower()
        assert "user" in exc_info.value.detail
    
    def test_role_checker_multiple_roles_success(self, test_user: User):
        """Test RoleChecker with multiple allowed roles - success."""
        # Ensure user has the correct user_type
        test_user.user_type = "user"
        checker = RoleChecker(["user", "vendor"])
        result = checker(test_user)
        assert result == test_user
    
    def test_role_checker_multiple_roles_vendor_success(self, test_vendor: Vendor):
        """Test RoleChecker with multiple allowed roles - vendor success."""
        # Ensure vendor has the correct user_type
        test_vendor.user_type = "vendor"
        checker = RoleChecker(["user", "vendor"])
        result = checker(test_vendor)
        assert result == test_vendor
    
    def test_role_checker_multiple_roles_failure(self, test_user: User):
        """Test RoleChecker with multiple allowed roles - failure."""
        test_user.user_type = "admin"  # Not in allowed roles
        checker = RoleChecker(["user", "vendor"])
        
        with pytest.raises(HTTPException) as exc_info:
            checker(test_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "user, vendor" in exc_info.value.detail


class TestPredefinedRoleCheckers:
    """Test predefined role checker instances."""
    
    def test_require_user_role_success(self, test_user: User):
        """Test require_user_role with user."""
        # Ensure user has the correct user_type
        test_user.user_type = "user"
        result = require_user_role(test_user)
        assert result == test_user
    
    def test_require_user_role_failure(self, test_vendor: Vendor):
        """Test require_user_role with vendor."""
        # Ensure vendor has vendor user_type
        test_vendor.user_type = "vendor"
        with pytest.raises(HTTPException) as exc_info:
            require_user_role(test_vendor)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_require_vendor_role_success(self, test_vendor: Vendor):
        """Test require_vendor_role with vendor."""
        # Ensure vendor has the correct user_type
        test_vendor.user_type = "vendor"
        result = require_vendor_role(test_vendor)
        assert result == test_vendor
    
    def test_require_vendor_role_failure(self, test_user: User):
        """Test require_vendor_role with user."""
        # Ensure user has user user_type
        test_user.user_type = "user"
        with pytest.raises(HTTPException) as exc_info:
            require_vendor_role(test_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_require_any_role_user_success(self, test_user: User):
        """Test require_any_role with user."""
        # Ensure user has the correct user_type
        test_user.user_type = "user"
        result = require_any_role(test_user)
        assert result == test_user
    
    def test_require_any_role_vendor_success(self, test_vendor: Vendor):
        """Test require_any_role with vendor."""
        # Ensure vendor has the correct user_type
        test_vendor.user_type = "vendor"
        result = require_any_role(test_vendor)
        assert result == test_vendor
    
    def test_require_any_role_failure(self, test_user: User):
        """Test require_any_role with invalid role."""
        test_user.user_type = "admin"  # Not user or vendor
        
        with pytest.raises(HTTPException) as exc_info:
            require_any_role(test_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestAdvancedVerificationScenarios:
    """Test advanced verification scenarios."""
    
    def test_require_verified_user_with_different_statuses(self):
        """Test require_verified_user with different verification statuses."""
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="user"
        )
        
        # Test each verification status
        verification_statuses = [
            (VerificationStatus.UNVERIFIED, False),
            (VerificationStatus.PHONE_VERIFIED, True),
            (VerificationStatus.DOCUMENT_VERIFIED, True),
            (VerificationStatus.FULLY_VERIFIED, True),
        ]
        
        for status_val, should_pass in verification_statuses:
            user.verification_status = status_val
            
            if should_pass:
                result = require_verified_user(user)
                assert result == user
            else:
                with pytest.raises(HTTPException) as exc_info:
                    require_verified_user(user)
                assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_require_verified_vendor_with_different_statuses(self):
        """Test require_verified_vendor with different verification statuses."""
        vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="vendor",
            business_name="Test Vendor",
            business_type=BusinessType.RETAILER
        )
        
        # Test each verification status
        verification_statuses = [
            (VerificationStatus.UNVERIFIED, False),
            (VerificationStatus.PHONE_VERIFIED, True),
            (VerificationStatus.DOCUMENT_VERIFIED, True),
            (VerificationStatus.FULLY_VERIFIED, True),
        ]
        
        for status_val, should_pass in verification_statuses:
            vendor.verification_status = status_val
            
            if should_pass:
                result = require_verified_vendor(vendor)
                assert result == vendor
            else:
                with pytest.raises(HTTPException) as exc_info:
                    require_verified_vendor(vendor)
                assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_trusted_vendor_criteria(self):
        """Test various criteria for trusted vendor status."""
        base_vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.ADVANCED,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="vendor",
            business_name="Test Vendor",
            business_type=BusinessType.WHOLESALER,
            rating=Decimal('4.5'),
            total_transactions=100,
            is_verified_business=True
        )
        
        # Test trusted vendor (should pass)
        result = require_trusted_vendor(base_vendor)
        assert result == base_vendor
        
        # Test various scenarios that should fail
        failing_scenarios = [
            # Low rating
            {"rating": Decimal('2.0'), "total_transactions": 100, "is_verified_business": True},
            # Few transactions
            {"rating": Decimal('4.5'), "total_transactions": 5, "is_verified_business": True},
            # Not verified business
            {"rating": Decimal('4.5'), "total_transactions": 100, "is_verified_business": False},
            # Unverified status
            {"rating": Decimal('4.5'), "total_transactions": 100, "is_verified_business": True, 
             "verification_status": VerificationStatus.UNVERIFIED},
        ]
        
        for scenario in failing_scenarios:
            test_vendor = Vendor(
                id=uuid4(),
                phone_number="+919876543212",
                preferred_language=LanguageCode.ENGLISH,
                location="Delhi, India",
                tech_literacy_level=TechLiteracyLevel.ADVANCED,
                verification_status=scenario.get("verification_status", VerificationStatus.FULLY_VERIFIED),
                user_type="vendor",
                business_name="Test Vendor 2",
                business_type=BusinessType.WHOLESALER,
                rating=scenario["rating"],
                total_transactions=scenario["total_transactions"],
                is_verified_business=scenario["is_verified_business"]
            )
            
            with pytest.raises(HTTPException) as exc_info:
                require_trusted_vendor(test_vendor)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestRoleCheckerAdvanced:
    """Test advanced role checker scenarios."""
    
    def test_role_checker_with_custom_roles(self):
        """Test RoleChecker with custom role definitions."""
        # Test with hypothetical admin role
        admin_checker = RoleChecker(["admin"])
        
        regular_user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            admin_checker(regular_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail
    
    def test_role_checker_case_sensitivity(self):
        """Test that role checking is case sensitive."""
        checker = RoleChecker(["User"])  # Capital U
        
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"  # lowercase u
        )
        
        with pytest.raises(HTTPException) as exc_info:
            checker(user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_role_checker_empty_roles_list(self):
        """Test RoleChecker with empty allowed roles list."""
        empty_checker = RoleChecker([])
        
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            empty_checker(user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_role_checker_with_none_user_type(self):
        """Test RoleChecker with None user type."""
        checker = RoleChecker(["user", "vendor"])
        
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type=None  # None user type
        )
        
        with pytest.raises(HTTPException) as exc_info:
            checker(user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestDependencyChaining:
    """Test chaining of authentication dependencies."""
    
    def test_verified_user_requires_auth(self):
        """Test that verified user dependency requires authentication."""
        # This tests the dependency chain: require_verified_user -> require_auth
        unverified_user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="user"
        )
        
        # Should fail verification check
        with pytest.raises(HTTPException) as exc_info:
            require_verified_user(unverified_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "verification required" in exc_info.value.detail.lower()
    
    def test_trusted_vendor_requires_verification(self):
        """Test that trusted vendor dependency requires verification."""
        # This tests the dependency chain: require_trusted_vendor -> require_verified_vendor -> require_vendor_auth
        unverified_vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="vendor",
            business_name="Unverified Vendor",
            business_type=BusinessType.RETAILER,
            rating=Decimal('4.5'),
            total_transactions=100,
            is_verified_business=True
        )
        
        # Should fail verification check before trusted check
        with pytest.raises(HTTPException) as exc_info:
            require_trusted_vendor(unverified_vendor)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        # The error should be about verification, not trusted status
        assert "verification required" in exc_info.value.detail.lower()


class TestErrorMessageConsistency:
    """Test consistency of error messages across dependencies."""
    
    def test_verification_error_messages(self):
        """Test that verification error messages are consistent and helpful."""
        unverified_user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="user"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            require_verified_user(unverified_user)
        
        error_detail = exc_info.value.detail.lower()
        assert "verification" in error_detail
        assert "required" in error_detail
        # Should provide actionable guidance
        assert any(word in error_detail for word in ["verify", "phone", "number"])
    
    def test_role_error_messages_include_required_roles(self):
        """Test that role error messages include the required roles."""
        checker = RoleChecker(["admin", "moderator"])
        
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            checker(user)
        
        error_detail = exc_info.value.detail
        assert "admin" in error_detail
        assert "moderator" in error_detail
        assert "access denied" in error_detail.lower()
    
    def test_trusted_vendor_error_message_guidance(self):
        """Test that trusted vendor error message provides guidance."""
        low_rating_vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="vendor",
            business_name="Low Rating Vendor",
            business_type=BusinessType.RETAILER,
            rating=Decimal('2.0'),
            total_transactions=10,
            is_verified_business=False
        )
        
        with pytest.raises(HTTPException) as exc_info:
            require_trusted_vendor(low_rating_vendor)
        
        error_detail = exc_info.value.detail.lower()
        assert "trusted vendor" in error_detail
        assert "required" in error_detail
        # Should provide actionable guidance
        assert any(word in error_detail for word in ["rating", "transactions", "improve"])


class TestDependencyPerformance:
    """Test performance characteristics of dependencies."""
    
    def test_dependency_execution_time(self):
        """Test that dependencies execute quickly."""
        import time
        
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        # Test multiple dependency calls
        start_time = time.time()
        
        for _ in range(100):
            require_auth(user)
            require_verified_user(user)
            require_any_role(user)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete 300 dependency checks in under 1 second
        assert execution_time < 1.0, f"Dependencies too slow: {execution_time:.3f}s"
    
    def test_role_checker_performance(self):
        """Test that role checker performs well with many roles."""
        import time
        
        # Create checker with many allowed roles
        many_roles = [f"role_{i}" for i in range(100)]
        checker = RoleChecker(many_roles)
        
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="role_50"  # Should be found in the middle
        )
        
        start_time = time.time()
        
        for _ in range(100):
            checker(user)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete 100 role checks in under 0.1 seconds
        assert execution_time < 0.1, f"Role checker too slow: {execution_time:.3f}s"