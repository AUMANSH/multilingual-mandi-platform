"""
Unit tests for authentication API endpoints.

This module tests the authentication REST API endpoints including
login, registration, logout, and token management.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.mandi_platform.main import app
from src.mandi_platform.models.user import User, Vendor
from src.mandi_platform.models.enums import (
    LanguageCode, 
    TechLiteracyLevel, 
    VerificationStatus, 
    BusinessType,
    MarketReputation
)


class TestLoginEndpoint:
    """Test login endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful user login."""
        # Mock user CRUD to return test user
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = test_user
            mock_crud.update_last_active.return_value = test_user
            
            response = await async_client.post(
                "/auth/login",
                json={"phone_number": "+919876543210"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user_id"] == str(test_user.id)
        assert data["user_type"] == "user"
        assert data["phone_number"] == "+919876543210"
        assert data["preferred_language"] == "hi"
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = None
            
            response = await async_client.post(
                "/auth/login",
                json={"phone_number": "+919876543210"}
            )
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid phone number" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_phone_format(self, async_client: AsyncClient):
        """Test login with invalid phone number format."""
        response = await async_client.post(
            "/auth/login",
            json={"phone_number": "invalid-phone"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_login_vendor_success(self, async_client: AsyncClient, test_vendor: Vendor):
        """Test successful vendor login."""
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = test_vendor
            mock_crud.update_last_active.return_value = test_vendor
            
            response = await async_client.post(
                "/auth/login",
                json={"phone_number": "+919876543211"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_type"] == "vendor"
        assert data["user_id"] == str(test_vendor.id)


class TestUserRegistrationEndpoint:
    """Test user registration endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        new_user = User(
            id=uuid4(),
            phone_number="+919876543212",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="user"
        )
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = None  # User doesn't exist
            mock_crud.create.return_value = new_user
            
            response = await async_client.post(
                "/auth/register",
                json={
                    "phone_number": "+919876543212",
                    "preferred_language": "hi",
                    "location": "Mumbai, Maharashtra, India",
                    "tech_literacy_level": "beginner"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user_type"] == "user"
        assert data["phone_number"] == "+919876543212"
    
    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, async_client: AsyncClient, test_user: User):
        """Test registration when user already exists."""
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = test_user  # User exists
            
            response = await async_client.post(
                "/auth/register",
                json={
                    "phone_number": "+919876543210",
                    "preferred_language": "hi",
                    "location": "Mumbai, Maharashtra, India",
                    "tech_literacy_level": "beginner"
                }
            )
        
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_register_user_invalid_data(self, async_client: AsyncClient):
        """Test registration with invalid data."""
        response = await async_client.post(
            "/auth/register",
            json={
                "phone_number": "invalid-phone",
                "preferred_language": "invalid-lang",
                "location": "Mumbai, Maharashtra, India",
                "tech_literacy_level": "invalid-level"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestVendorRegistrationEndpoint:
    """Test vendor registration endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_register_vendor_success(self, async_client: AsyncClient):
        """Test successful vendor registration."""
        new_vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543213",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="vendor",
            business_name="New Test Business",
            business_type=BusinessType.RETAILER
        )
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_user_crud, \
             patch("src.mandi_platform.api.auth.vendor_crud") as mock_vendor_crud:
            
            mock_user_crud.get_by_phone.return_value = None  # User doesn't exist
            mock_vendor_crud.get_by_business_name.return_value = None  # Business name available
            mock_vendor_crud.create.return_value = new_vendor
            
            response = await async_client.post(
                "/auth/register-vendor",
                json={
                    "phone_number": "+919876543213",
                    "preferred_language": "en",
                    "location": "Delhi, India",
                    "tech_literacy_level": "intermediate",
                    "business_name": "New Test Business",
                    "business_type": "retailer"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user_type"] == "vendor"
        assert data["phone_number"] == "+919876543213"
    
    @pytest.mark.asyncio
    async def test_register_vendor_business_name_exists(self, async_client: AsyncClient, test_vendor: Vendor):
        """Test vendor registration when business name already exists."""
        with patch("src.mandi_platform.api.auth.user_crud") as mock_user_crud, \
             patch("src.mandi_platform.api.auth.vendor_crud") as mock_vendor_crud:
            
            mock_user_crud.get_by_phone.return_value = None  # User doesn't exist
            mock_vendor_crud.get_by_business_name.return_value = test_vendor  # Business name taken
            
            response = await async_client.post(
                "/auth/register-vendor",
                json={
                    "phone_number": "+919876543213",
                    "preferred_language": "en",
                    "location": "Delhi, India",
                    "tech_literacy_level": "intermediate",
                    "business_name": "Test Vendor Business",  # Same as test_vendor
                    "business_type": "retailer"
                }
            )
        
        assert response.status_code == 400
        data = response.json()
        assert "Business name already exists" in data["detail"]


class TestAuthenticatedEndpoints:
    """Test endpoints that require authentication."""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await async_client.post(
            "/auth/logout",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out" in data["message"]
    
    @pytest.mark.asyncio
    async def test_logout_unauthorized(self, async_client: AsyncClient):
        """Test logout without authentication."""
        response = await async_client.post(
            "/auth/logout",
            json={}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_logout_with_expired_token(self, async_client: AsyncClient):
        """Test logout with expired token."""
        # Create an expired token
        from datetime import timedelta
        from src.mandi_platform.auth.jwt import create_access_token
        
        expired_token_data = {
            "sub": str(uuid4()),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        expired_token = create_access_token(expired_token_data, expires_delta=timedelta(seconds=-1))
        
        response = await async_client.post(
            "/auth/logout",
            json={},
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_logout_with_malformed_token(self, async_client: AsyncClient):
        """Test logout with malformed token."""
        response = await async_client.post(
            "/auth/logout",
            json={},
            headers={"Authorization": "Bearer malformed.token.here"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_info(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test getting current user information."""
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            response = await async_client.get(
                "/auth/me",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_user.id)
        assert data["phone_number"] == test_user.phone_number
        assert data["user_type"] == "user"
        assert data["preferred_language"] == "hi"
    
    @pytest.mark.asyncio
    async def test_get_vendor_info(self, async_client: AsyncClient, vendor_auth_headers: dict, test_vendor: Vendor):
        """Test getting current vendor information."""
        with patch("src.mandi_platform.auth.jwt.vendor_crud") as mock_crud:
            mock_crud.get.return_value = test_vendor
            
            response = await async_client.get(
                "/auth/me",
                headers=vendor_auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_vendor.id)
        assert data["user_type"] == "vendor"
        assert data["business_name"] == test_vendor.business_name
        assert "rating" in data
        assert "total_transactions" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test token refresh."""
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            response = await async_client.post(
                "/auth/refresh",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_verify_token(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test token verification."""
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            response = await async_client.get(
                "/auth/verify-token",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["user_id"] == str(test_user.id)
        assert data["user_type"] == "user"
    
    @pytest.mark.asyncio
    async def test_verify_expired_token(self, async_client: AsyncClient, test_user: User):
        """Test verification of expired token."""
        from datetime import timedelta
        from src.mandi_platform.auth.jwt import create_access_token, create_user_token
        
        # Create expired token
        token_data = create_user_token(test_user)
        expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))
        
        response = await async_client.get(
            "/auth/verify-token",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_user_not_found(self, async_client: AsyncClient, auth_headers: dict):
        """Test token verification when user no longer exists."""
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = None  # User not found
            
            response = await async_client.get(
                "/auth/verify-token",
                headers=auth_headers
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid_format(self, async_client: AsyncClient):
        """Test token verification with invalid token format."""
        response = await async_client.get(
            "/auth/verify-token",
            headers={"Authorization": "Bearer invalid.token.format"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_missing_authorization(self, async_client: AsyncClient):
        """Test token verification without authorization header."""
        response = await async_client.get("/auth/verify-token")
        
        assert response.status_code == 401


class TestRoleBasedAccessControl:
    """Test role-based access control functionality."""
    
    @pytest.mark.asyncio
    async def test_user_access_to_user_endpoint(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test user can access user-specific endpoints."""
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            response = await async_client.get(
                "/auth/me",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "user"
    
    @pytest.mark.asyncio
    async def test_vendor_access_to_vendor_endpoint(self, async_client: AsyncClient, vendor_auth_headers: dict, test_vendor: Vendor):
        """Test vendor can access vendor-specific endpoints."""
        with patch("src.mandi_platform.auth.jwt.vendor_crud") as mock_crud:
            mock_crud.get.return_value = test_vendor
            
            response = await async_client.get(
                "/auth/me",
                headers=vendor_auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "vendor"
        assert "business_name" in data
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_vendor_only_endpoint(self, async_client: AsyncClient, auth_headers: dict):
        """Test user cannot access vendor-only endpoints."""
        # This would be tested with actual vendor-only endpoints when they exist
        # For now, we test the principle with the JWT validation
        from src.mandi_platform.auth.jwt import get_current_vendor
        from fastapi.security import HTTPAuthorizationCredentials
        from unittest.mock import AsyncMock
        
        # Create user token but try to get vendor
        user_token_data = {
            "sub": str(uuid4()),
            "user_type": "user",  # User, not vendor
            "phone_number": "+919876543210"
        }
        
        from src.mandi_platform.auth.jwt import create_access_token
        token = create_access_token(user_token_data)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_vendor(credentials, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Vendor privileges required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_token_with_wrong_user_type_rejected(self, async_client: AsyncClient):
        """Test token with invalid user type is rejected."""
        # Create token with invalid user type
        invalid_token_data = {
            "sub": str(uuid4()),
            "user_type": "admin",  # Invalid user type
            "phone_number": "+919876543210"
        }
        
        from src.mandi_platform.auth.jwt import create_access_token
        token = create_access_token(invalid_token_data)
        
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail because admin is not a valid user type in our system
        assert response.status_code == 401


class TestTokenExpiration:
    """Test token expiration and refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_token_refresh_success(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test successful token refresh."""
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            response = await async_client.post(
                "/auth/refresh",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # New token should be different from the original
        original_token = auth_headers["Authorization"].split(" ")[1]
        assert data["access_token"] != original_token
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_expired_token(self, async_client: AsyncClient, test_user: User):
        """Test token refresh with expired token fails."""
        from datetime import timedelta
        from src.mandi_platform.auth.jwt import create_access_token, create_user_token
        
        # Create expired token
        token_data = create_user_token(test_user)
        expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))
        
        response = await async_client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_refresh_unauthorized(self, async_client: AsyncClient):
        """Test token refresh without authentication."""
        response = await async_client.post("/auth/refresh")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_expiration_time_validation(self):
        """Test that tokens have correct expiration time."""
        from src.mandi_platform.auth.jwt import create_access_token, get_token_expires_in
        from jose import jwt
        from src.mandi_platform.config import settings
        import time
        
        token_data = {
            "sub": str(uuid4()),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        
        before_creation = time.time()
        token = create_access_token(token_data)
        after_creation = time.time()
        
        # Decode token to check expiration
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        token_exp = payload["exp"]
        
        expected_exp_min = before_creation + get_token_expires_in()
        expected_exp_max = after_creation + get_token_expires_in()
        
        assert expected_exp_min <= token_exp <= expected_exp_max


class TestSecurityEdgeCases:
    """Test security edge cases and attack scenarios."""
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_phone_number(self, async_client: AsyncClient):
        """Test SQL injection attempt in phone number field."""
        malicious_phone = "+91'; DROP TABLE users; --"
        
        response = await async_client.post(
            "/auth/login",
            json={"phone_number": malicious_phone}
        )
        
        # Should fail validation, not cause SQL injection
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_xss_in_business_name(self, async_client: AsyncClient):
        """Test XSS attempt in business name field."""
        malicious_business_name = "<script>alert('xss')</script>"
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_user_crud, \
             patch("src.mandi_platform.api.auth.vendor_crud") as mock_vendor_crud:
            
            mock_user_crud.get_by_phone.return_value = None
            mock_vendor_crud.get_by_business_name.return_value = None
            
            response = await async_client.post(
                "/auth/register-vendor",
                json={
                    "phone_number": "+919876543214",
                    "preferred_language": "en",
                    "location": "Delhi, India",
                    "tech_literacy_level": "intermediate",
                    "business_name": malicious_business_name,
                    "business_type": "retailer"
                }
            )
        
        # Should either succeed (if properly sanitized) or fail validation
        # The important thing is it doesn't execute the script
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_token_tampering_detection(self, async_client: AsyncClient):
        """Test detection of tampered JWT tokens."""
        from src.mandi_platform.auth.jwt import create_access_token
        
        # Create valid token
        token_data = {
            "sub": str(uuid4()),
            "user_type": "user",
            "phone_number": "+919876543210"
        }
        valid_token = create_access_token(token_data)
        
        # Tamper with the token (change last character)
        tampered_token = valid_token[:-1] + ("a" if valid_token[-1] != "a" else "b")
        
        response = await async_client.get(
            "/auth/verify-token",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_concurrent_login_attempts(self, async_client: AsyncClient, test_user: User):
        """Test handling of concurrent login attempts."""
        import asyncio
        
        async def login_attempt():
            with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
                mock_crud.get_by_phone.return_value = test_user
                mock_crud.update_last_active.return_value = test_user
                
                return await async_client.post(
                    "/auth/login",
                    json={"phone_number": "+919876543210"}
                )
        
        # Make multiple concurrent login attempts
        tasks = [login_attempt() for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed (no race conditions)
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_token_reuse_after_logout(self, async_client: AsyncClient, auth_headers: dict, test_user: User):
        """Test that tokens cannot be reused after logout."""
        # First, logout
        logout_response = await async_client.post(
            "/auth/logout",
            json={},
            headers=auth_headers
        )
        assert logout_response.status_code == 200
        
        # Try to use the same token after logout
        # Note: In this simple implementation, tokens are not blacklisted
        # This test documents the current behavior and can be updated
        # when token blacklisting is implemented
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            response = await async_client.get(
                "/auth/me",
                headers=auth_headers
            )
        
        # Currently, token still works (no blacklisting implemented)
        # This test documents the current behavior
        assert response.status_code == 200
        
        # TODO: When token blacklisting is implemented, this should return 401
    
    @pytest.mark.asyncio
    async def test_rate_limiting_login_attempts(self, async_client: AsyncClient):
        """Test rate limiting of login attempts."""
        # This test would be more meaningful with actual rate limiting
        # For now, we test that multiple failed attempts don't crash the system
        
        failed_attempts = []
        for i in range(10):
            with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
                mock_crud.get_by_phone.return_value = None  # User not found
                
                response = await async_client.post(
                    "/auth/login",
                    json={"phone_number": f"+9198765432{i:02d}"}
                )
                failed_attempts.append(response)
        
        # All should fail gracefully
        for response in failed_attempts:
            assert response.status_code == 401
            data = response.json()
            assert "Invalid phone number" in data["detail"]


class TestAuthenticationFlowIntegration:
    """Test complete authentication flow integration."""
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_and_login_flow(self, async_client: AsyncClient):
        """Test complete user registration and login flow."""
        phone_number = "+919876543299"
        
        # Step 1: Register new user
        new_user = User(
            id=uuid4(),
            phone_number=phone_number,
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="user"
        )
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = None  # User doesn't exist
            mock_crud.create.return_value = new_user
            
            register_response = await async_client.post(
                "/auth/register",
                json={
                    "phone_number": phone_number,
                    "preferred_language": "hi",
                    "location": "Mumbai, Maharashtra, India",
                    "tech_literacy_level": "beginner"
                }
            )
        
        assert register_response.status_code == 200
        register_data = register_response.json()
        assert "access_token" in register_data
        
        # Step 2: Use token to access protected endpoint
        token = register_data["access_token"]
        
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = new_user
            
            me_response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["phone_number"] == phone_number
        
        # Step 3: Login with same credentials
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = new_user
            mock_crud.update_last_active.return_value = new_user
            
            login_response = await async_client.post(
                "/auth/login",
                json={"phone_number": phone_number}
            )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        
        # Step 4: Logout
        logout_response = await async_client.post(
            "/auth/logout",
            json={},
            headers={"Authorization": f"Bearer {login_data['access_token']}"}
        )
        
        assert logout_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_complete_vendor_registration_and_access_flow(self, async_client: AsyncClient):
        """Test complete vendor registration and access flow."""
        phone_number = "+919876543298"
        business_name = "Test Integration Vendor"
        
        # Step 1: Register new vendor
        new_vendor = Vendor(
            id=uuid4(),
            phone_number=phone_number,
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.UNVERIFIED,
            user_type="vendor",
            business_name=business_name,
            business_type=BusinessType.RETAILER
        )
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_user_crud, \
             patch("src.mandi_platform.api.auth.vendor_crud") as mock_vendor_crud:
            
            mock_user_crud.get_by_phone.return_value = None
            mock_vendor_crud.get_by_business_name.return_value = None
            mock_vendor_crud.create.return_value = new_vendor
            
            register_response = await async_client.post(
                "/auth/register-vendor",
                json={
                    "phone_number": phone_number,
                    "preferred_language": "en",
                    "location": "Delhi, India",
                    "tech_literacy_level": "intermediate",
                    "business_name": business_name,
                    "business_type": "retailer"
                }
            )
        
        assert register_response.status_code == 200
        register_data = register_response.json()
        assert "access_token" in register_data
        assert register_data["user_type"] == "vendor"
        
        # Step 2: Access vendor-specific information
        token = register_data["access_token"]
        
        with patch("src.mandi_platform.auth.jwt.vendor_crud") as mock_crud:
            mock_crud.get.return_value = new_vendor
            
            me_response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["business_name"] == business_name
        assert me_data["user_type"] == "vendor"
        assert "rating" in me_data
        assert "total_transactions" in me_data