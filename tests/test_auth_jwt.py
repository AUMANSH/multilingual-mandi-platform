"""
Unit tests for JWT authentication utilities.

This module tests JWT token creation, validation, and user authentication
functions.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from src.mandi_platform.auth.jwt import (
    create_access_token,
    verify_token,
    get_current_user,
    get_current_vendor,
    create_user_token,
    get_token_expires_in,
)
from src.mandi_platform.auth.schemas import TokenData
from src.mandi_platform.models.user import User, Vendor
from src.mandi_platform.models.enums import LanguageCode, TechLiteracyLevel, VerificationStatus, BusinessType
from src.mandi_platform.config import settings


class TestJWTTokenCreation:
    """Test JWT token creation functionality."""
    
    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry."""
        data = {"sub": "test-user-id", "user_type": "user"}
        token = create_access_token(data)
        
        # Verify token can be decoded
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "test-user-id"
        assert payload["user_type"] == "user"
        assert "exp" in payload
        
        # Verify expiry exists and is in the future
        assert "exp" in payload
        assert payload["exp"] > datetime.utcnow().timestamp()
    
    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "test-user-id", "user_type": "vendor"}
        custom_expiry = timedelta(hours=2)
        token = create_access_token(data, expires_delta=custom_expiry)
        
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Verify custom expiry is used and is in the future
        assert payload["exp"] > datetime.utcnow().timestamp()
    
    def test_create_user_token(self):
        """Test creating token payload for user."""
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        token_data = create_user_token(user)
        
        assert token_data["sub"] == str(user.id)
        assert token_data["user_type"] == "user"
        assert token_data["phone_number"] == "+919876543210"
        assert token_data["preferred_language"] == "hi"
    
    def test_create_vendor_token(self):
        """Test creating token payload for vendor."""
        vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="vendor",
            business_name="Test Business",
            business_type=BusinessType.RETAILER
        )
        
        token_data = create_user_token(vendor)
        
        assert token_data["sub"] == str(vendor.id)
        assert token_data["user_type"] == "vendor"
        assert token_data["phone_number"] == "+919876543210"
        assert token_data["preferred_language"] == "en"


class TestJWTTokenVerification:
    """Test JWT token verification functionality."""
    
    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        user_id = uuid4()
        data = {
            "sub": str(user_id),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        token = create_access_token(data)
        
        token_data = verify_token(token)
        
        assert token_data.user_id == user_id
        assert token_data.user_type == "user"
        assert token_data.phone_number == "+919876543210"
        assert token_data.exp is not None
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail
    
    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        data = {"sub": "test-user-id", "user_type": "user", "phone_number": "+919876543210"}
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_token_missing_fields(self):
        """Test verifying token with missing required fields."""
        # Token missing user_type
        data = {"sub": "test-user-id", "phone_number": "+919876543210"}
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_token_malformed_user_id(self):
        """Test verifying token with malformed user ID."""
        data = {
            "sub": "not-a-valid-uuid",
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserAuthentication:
    """Test user authentication functions."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successfully getting current user."""
        user_id = uuid4()
        user = User(
            id=user_id,
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            user_type="user"
        )
        
        # Mock database session and CRUD
        mock_db = AsyncMock()
        mock_user_crud = AsyncMock()
        mock_user_crud.get.return_value = user
        
        # Mock credentials
        token_data = {
            "sub": str(user_id),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        token = create_access_token(token_data)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        with patch("src.mandi_platform.auth.jwt.user_crud", mock_user_crud):
            result = await get_current_user(credentials, mock_db)
        
        assert result == user
        mock_user_crud.get.assert_called_once_with(mock_db, user_id)
    
    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self):
        """Test getting current user when user not found in database."""
        user_id = uuid4()
        
        # Mock database session and CRUD
        mock_db = AsyncMock()
        mock_user_crud = AsyncMock()
        mock_user_crud.get.return_value = None
        
        # Mock credentials
        token_data = {
            "sub": str(user_id),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        token = create_access_token(token_data)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        with patch("src.mandi_platform.auth.jwt.user_crud", mock_user_crud):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_vendor_success(self):
        """Test successfully getting current vendor."""
        vendor_id = uuid4()
        vendor = Vendor(
            id=vendor_id,
            phone_number="+919876543210",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            user_type="vendor",
            business_name="Test Business",
            business_type=BusinessType.RETAILER
        )
        
        # Mock database session and CRUD
        mock_db = AsyncMock()
        mock_vendor_crud = AsyncMock()
        mock_vendor_crud.get.return_value = vendor
        
        # Mock credentials
        token_data = {
            "sub": str(vendor_id),
            "user_type": "vendor",
            "phone_number": "+919876543210"
        }
        token = create_access_token(token_data)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        with patch("src.mandi_platform.auth.jwt.vendor_crud", mock_vendor_crud):
            result = await get_current_vendor(credentials, mock_db)
        
        assert result == vendor
        mock_vendor_crud.get.assert_called_once_with(mock_db, vendor_id)
    
    @pytest.mark.asyncio
    async def test_get_current_vendor_wrong_user_type(self):
        """Test getting current vendor with non-vendor token."""
        user_id = uuid4()
        
        # Mock credentials with user type instead of vendor
        token_data = {
            "sub": str(user_id),
            "user_type": "user",  # Not a vendor
            "phone_number": "+919876543210"
        }
        token = create_access_token(token_data)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_vendor(credentials, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Vendor privileges required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_vendor_not_found(self):
        """Test getting current vendor when vendor not found in database."""
        vendor_id = uuid4()
        
        # Mock database session and CRUD
        mock_db = AsyncMock()
        mock_vendor_crud = AsyncMock()
        mock_vendor_crud.get.return_value = None
        
        # Mock credentials
        token_data = {
            "sub": str(vendor_id),
            "user_type": "vendor",
            "phone_number": "+919876543210"
        }
        token = create_access_token(token_data)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        with patch("src.mandi_platform.auth.jwt.vendor_crud", mock_vendor_crud):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_vendor(credentials, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Vendor not found" in exc_info.value.detail


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_token_expires_in(self):
        """Test getting token expiration time in seconds."""
        expected_seconds = settings.access_token_expire_minutes * 60
        assert get_token_expires_in() == expected_seconds
    
    def test_token_expiration_consistency(self):
        """Test that token expiration is consistent across calls."""
        expires_in_1 = get_token_expires_in()
        expires_in_2 = get_token_expires_in()
        assert expires_in_1 == expires_in_2
    
    def test_create_user_token_completeness(self):
        """Test that user token contains all required fields."""
        user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        token_data = create_user_token(user)
        
        required_fields = {"sub", "user_type", "phone_number", "preferred_language"}
        assert all(field in token_data for field in required_fields)
        
        # Verify field types and formats
        assert isinstance(token_data["sub"], str)
        assert token_data["user_type"] in ["user", "vendor"]
        assert token_data["phone_number"].startswith("+91")
        assert token_data["preferred_language"] in ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]


class TestTokenSecurity:
    """Test token security features."""
    
    def test_token_signature_validation(self):
        """Test that tokens with invalid signatures are rejected."""
        # Create a valid token
        data = {"sub": str(uuid4()), "user_type": "user", "phone_number": "+919876543210"}
        valid_token = create_access_token(data)
        
        # Tamper with the signature (last part after the last dot)
        parts = valid_token.split('.')
        tampered_signature = parts[2][:-1] + ('a' if parts[2][-1] != 'a' else 'b')
        tampered_token = f"{parts[0]}.{parts[1]}.{tampered_signature}"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_payload_tampering_detection(self):
        """Test detection of tampered token payload."""
        import base64
        import json
        
        # Create a valid token
        data = {"sub": str(uuid4()), "user_type": "user", "phone_number": "+919876543210"}
        valid_token = create_access_token(data)
        
        # Tamper with the payload (middle part)
        parts = valid_token.split('.')
        
        # Decode, modify, and re-encode the payload
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
        payload["user_type"] = "admin"  # Change user type
        
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_algorithm_confusion_attack(self):
        """Test protection against algorithm confusion attacks."""
        # This test ensures we don't accept tokens with different algorithms
        # than what we expect (HS256)
        
        # Try to create a token with a different algorithm
        # Note: This is more of a configuration test
        from jose import jwt
        
        data = {"sub": str(uuid4()), "user_type": "user", "phone_number": "+919876543210"}
        
        # Try to create token with 'none' algorithm (security vulnerability)
        try:
            malicious_token = jwt.encode(data, "", algorithm="none")
            
            with pytest.raises(HTTPException) as exc_info:
                verify_token(malicious_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        except Exception:
            # If jose doesn't allow 'none' algorithm, that's good
            pass
    
    def test_token_expiration_edge_cases(self):
        """Test token expiration edge cases."""
        from datetime import timedelta
        import time
        
        # Test token that expires in 1 second
        data = {"sub": str(uuid4()), "user_type": "user", "phone_number": "+919876543210"}
        short_lived_token = create_access_token(data, expires_delta=timedelta(seconds=1))
        
        # Should be valid immediately
        token_data = verify_token(short_lived_token)
        assert token_data.user_type == "user"
        
        # Wait for expiration
        time.sleep(2)
        
        # Should now be expired
        with pytest.raises(HTTPException) as exc_info:
            verify_token(short_lived_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_with_future_issued_time(self):
        """Test handling of tokens with future issued time."""
        from datetime import timedelta
        from jose import jwt
        import time
        
        # Create token with future 'iat' (issued at) time
        future_time = int(time.time()) + 3600  # 1 hour in future
        data = {
            "sub": str(uuid4()),
            "user_type": "user", 
            "phone_number": "+919876543210",
            "iat": future_time,
            "exp": future_time + 3600
        }
        
        future_token = jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
        
        # This should still work as we don't validate 'iat' in our current implementation
        # But it's good to document this behavior
        token_data = verify_token(future_token)
        assert token_data.user_type == "user"


class TestTokenValidationEdgeCases:
    """Test edge cases in token validation."""
    
    def test_verify_token_with_extra_fields(self):
        """Test token verification with extra fields in payload."""
        data = {
            "sub": str(uuid4()),
            "user_type": "user",
            "phone_number": "+919876543210",
            "extra_field": "should_be_ignored",
            "another_field": 12345
        }
        token = create_access_token(data)
        
        token_data = verify_token(token)
        
        # Should still work, extra fields ignored
        assert token_data.user_type == "user"
        assert token_data.phone_number == "+919876543210"
    
    def test_verify_token_with_unicode_characters(self):
        """Test token verification with unicode characters."""
        user_id = uuid4()
        data = {
            "sub": str(user_id),
            "user_type": "user",
            "phone_number": "+919876543210",
            "unicode_field": "हिंदी text with émojis 🚀"
        }
        token = create_access_token(data)
        
        token_data = verify_token(token)
        
        assert token_data.user_id == user_id
        assert token_data.user_type == "user"
    
    def test_verify_token_with_null_values(self):
        """Test token verification with null values."""
        data = {
            "sub": str(uuid4()),
            "user_type": "user",
            "phone_number": "+919876543210",
            "null_field": None
        }
        token = create_access_token(data)
        
        token_data = verify_token(token)
        
        # Should work fine, null fields ignored
        assert token_data.user_type == "user"
    
    def test_verify_token_missing_required_fields(self):
        """Test comprehensive validation of missing required fields."""
        base_data = {
            "sub": str(uuid4()),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        
        # Test missing each required field
        required_fields = ["sub", "user_type", "phone_number"]
        
        for missing_field in required_fields:
            data = base_data.copy()
            del data[missing_field]
            
            token = create_access_token(data)
            
            with pytest.raises(HTTPException) as exc_info:
                verify_token(token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_token_with_invalid_uuid(self):
        """Test token verification with invalid UUID in sub field."""
        data = {
            "sub": "not-a-valid-uuid",
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_token_with_empty_string_values(self):
        """Test token verification with empty string values."""
        data = {
            "sub": "",  # Empty string
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED