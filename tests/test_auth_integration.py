"""
Integration tests for authentication system.

This module tests the complete authentication system integration including
API endpoints, JWT handling, middleware, and dependencies working together.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import timedelta

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
from src.mandi_platform.auth.jwt import create_access_token, create_user_token


class TestAuthenticationSystemIntegration:
    """Test complete authentication system integration."""
    
    @pytest.mark.asyncio
    async def test_full_authentication_flow_with_middleware(self, async_client: AsyncClient):
        """Test complete authentication flow including middleware processing."""
        # Create test user
        test_user = User(
            id=uuid4(),
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        # Step 1: Register user
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = None  # User doesn't exist
            mock_crud.create.return_value = test_user
            
            register_response = await async_client.post(
                "/auth/register",
                json={
                    "phone_number": "+919876543210",
                    "preferred_language": "hi",
                    "location": "Mumbai, Maharashtra, India",
                    "tech_literacy_level": "beginner"
                }
            )
        
        assert register_response.status_code == 200
        register_data = register_response.json()
        token = register_data["access_token"]
        
        # Step 2: Use token to access protected endpoint (middleware should process this)
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            protected_response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert protected_response.status_code == 200
        user_data = protected_response.json()
        assert user_data["phone_number"] == "+919876543210"
        
        # Step 3: Refresh token
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            refresh_response = await async_client.post(
                "/auth/refresh",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        new_token = refresh_data["access_token"]
        assert new_token != token
        
        # Step 4: Use new token
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            mock_crud.get.return_value = test_user
            
            new_token_response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {new_token}"}
            )
        
        assert new_token_response.status_code == 200
        
        # Step 5: Logout
        logout_response = await async_client.post(
            "/auth/logout",
            json={},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        assert logout_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_vendor_specific_authentication_flow(self, async_client: AsyncClient):
        """Test vendor-specific authentication and authorization flow."""
        # Create test vendor
        test_vendor = Vendor(
            id=uuid4(),
            phone_number="+919876543211",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="vendor",
            business_name="Test Integration Vendor",
            business_type=BusinessType.RETAILER
        )
        
        # Step 1: Register vendor
        with patch("src.mandi_platform.api.auth.user_crud") as mock_user_crud, \
             patch("src.mandi_platform.api.auth.vendor_crud") as mock_vendor_crud:
            
            mock_user_crud.get_by_phone.return_value = None
            mock_vendor_crud.get_by_business_name.return_value = None
            mock_vendor_crud.create.return_value = test_vendor
            
            register_response = await async_client.post(
                "/auth/register-vendor",
                json={
                    "phone_number": "+919876543211",
                    "preferred_language": "en",
                    "location": "Delhi, India",
                    "tech_literacy_level": "intermediate",
                    "business_name": "Test Integration Vendor",
                    "business_type": "retailer"
                }
            )
        
        assert register_response.status_code == 200
        register_data = register_response.json()
        assert register_data["user_type"] == "vendor"
        vendor_token = register_data["access_token"]
        
        # Step 2: Access vendor-specific information
        with patch("src.mandi_platform.auth.jwt.vendor_crud") as mock_crud:
            mock_crud.get.return_value = test_vendor
            
            vendor_info_response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {vendor_token}"}
            )
        
        assert vendor_info_response.status_code == 200
        vendor_data = vendor_info_response.json()
        assert vendor_data["business_name"] == "Test Integration Vendor"
        assert "rating" in vendor_data
        assert "total_transactions" in vendor_data
    
    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self, async_client: AsyncClient):
        """Test handling of concurrent authentication requests."""
        test_user = User(
            id=uuid4(),
            phone_number="+919876543212",
            preferred_language=LanguageCode.TAMIL,
            location="Chennai, Tamil Nadu, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        async def login_request():
            with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
                mock_crud.get_by_phone.return_value = test_user
                mock_crud.update_last_active.return_value = test_user
                
                return await async_client.post(
                    "/auth/login",
                    json={"phone_number": "+919876543212"}
                )
        
        # Make 10 concurrent login requests
        tasks = [login_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["user_type"] == "user"
    
    @pytest.mark.asyncio
    async def test_authentication_with_invalid_middleware_state(self, async_client: AsyncClient):
        """Test authentication behavior with various middleware states."""
        test_user = User(
            id=uuid4(),
            phone_number="+919876543213",
            preferred_language=LanguageCode.GUJARATI,
            location="Ahmedabad, Gujarat, India",
            tech_literacy_level=TechLiteracyLevel.ADVANCED,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="user"
        )
        
        # Create valid token
        token_data = create_user_token(test_user)
        valid_token = create_access_token(token_data)
        
        # Test with various invalid token formats
        invalid_tokens = [
            "Bearer invalid-token",
            "Basic dXNlcjpwYXNz",  # Basic auth instead of Bearer
            "Bearer ",  # Empty token
            "invalid-format",  # No Bearer prefix
            "",  # Empty authorization
        ]
        
        for invalid_token in invalid_tokens:
            response = await async_client.get(
                "/auth/me",
                headers={"Authorization": invalid_token} if invalid_token else {}
            )
            
            # Should be unauthorized
            assert response.status_code == 401


class TestAuthenticationErrorHandling:
    """Test error handling in authentication system."""
    
    @pytest.mark.asyncio
    async def test_database_error_during_login(self, async_client: AsyncClient):
        """Test handling of database errors during login."""
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            # Simulate database error
            mock_crud.get_by_phone.side_effect = Exception("Database connection failed")
            
            response = await async_client.post(
                "/auth/login",
                json={"phone_number": "+919876543210"}
            )
        
        # Should return 500 internal server error
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_database_error_during_registration(self, async_client: AsyncClient):
        """Test handling of database errors during registration."""
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = None  # User doesn't exist
            # Simulate database error during creation
            mock_crud.create.side_effect = Exception("Database write failed")
            
            response = await async_client.post(
                "/auth/register",
                json={
                    "phone_number": "+919876543214",
                    "preferred_language": "hi",
                    "location": "Mumbai, Maharashtra, India",
                    "tech_literacy_level": "beginner"
                }
            )
        
        # Should return 500 internal server error
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_jwt_creation_error(self, async_client: AsyncClient):
        """Test handling of JWT creation errors."""
        test_user = User(
            id=uuid4(),
            phone_number="+919876543215",
            preferred_language=LanguageCode.BENGALI,
            location="Kolkata, West Bengal, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud, \
             patch("src.mandi_platform.api.auth.create_access_token") as mock_jwt:
            
            mock_crud.get_by_phone.return_value = test_user
            mock_crud.update_last_active.return_value = test_user
            # Simulate JWT creation error
            mock_jwt.side_effect = Exception("JWT creation failed")
            
            response = await async_client.post(
                "/auth/login",
                json={"phone_number": "+919876543215"}
            )
        
        # Should return 500 internal server error
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_malformed_request_data(self, async_client: AsyncClient):
        """Test handling of malformed request data."""
        # Test various malformed requests
        malformed_requests = [
            {},  # Empty request
            {"phone_number": None},  # Null phone number
            {"phone_number": 123456789},  # Integer instead of string
            {"phone_number": "+919876543210", "preferred_language": None},  # Null language
            {"phone_number": "+919876543210", "tech_literacy_level": "invalid"},  # Invalid enum
        ]
        
        for malformed_data in malformed_requests:
            response = await async_client.post(
                "/auth/register",
                json=malformed_data
            )
            
            # Should return validation error
            assert response.status_code == 422


class TestAuthenticationSecurity:
    """Test security aspects of authentication system."""
    
    @pytest.mark.asyncio
    async def test_token_hijacking_prevention(self, async_client: AsyncClient):
        """Test prevention of token hijacking attacks."""
        # Create two different users
        user1 = User(
            id=uuid4(),
            phone_number="+919876543216",
            preferred_language=LanguageCode.HINDI,
            location="Mumbai, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        user2 = User(
            id=uuid4(),
            phone_number="+919876543217",
            preferred_language=LanguageCode.ENGLISH,
            location="Delhi, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        # Create token for user1
        token_data = create_user_token(user1)
        user1_token = create_access_token(token_data)
        
        # Try to use user1's token to access user2's data
        with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
            # Return user2 when token validation looks up the user
            # This simulates a scenario where token validation is bypassed
            mock_crud.get.return_value = user2
            
            response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {user1_token}"}
            )
        
        # Should return user1's data (from token), not user2's data
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user1.id)  # Should match token's user ID
    
    @pytest.mark.asyncio
    async def test_brute_force_protection_simulation(self, async_client: AsyncClient):
        """Test simulation of brute force attack protection."""
        # Simulate multiple failed login attempts
        failed_attempts = []
        
        for i in range(20):  # 20 failed attempts
            with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
                mock_crud.get_by_phone.return_value = None  # User not found
                
                response = await async_client.post(
                    "/auth/login",
                    json={"phone_number": f"+9198765432{i:02d}"}
                )
                failed_attempts.append(response)
        
        # All should fail gracefully without crashing
        for response in failed_attempts:
            assert response.status_code == 401
            data = response.json()
            assert "Invalid phone number" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_session_fixation_prevention(self, async_client: AsyncClient):
        """Test prevention of session fixation attacks."""
        test_user = User(
            id=uuid4(),
            phone_number="+919876543218",
            preferred_language=LanguageCode.MARATHI,
            location="Pune, Maharashtra, India",
            tech_literacy_level=TechLiteracyLevel.ADVANCED,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="user"
        )
        
        # Login twice and ensure different tokens are generated
        tokens = []
        
        for _ in range(2):
            with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
                mock_crud.get_by_phone.return_value = test_user
                mock_crud.update_last_active.return_value = test_user
                
                response = await async_client.post(
                    "/auth/login",
                    json={"phone_number": "+919876543218"}
                )
                
                assert response.status_code == 200
                data = response.json()
                tokens.append(data["access_token"])
        
        # Tokens should be different (no session fixation)
        assert tokens[0] != tokens[1]
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_prevention(self, async_client: AsyncClient):
        """Test prevention of privilege escalation attacks."""
        # Create regular user
        regular_user = User(
            id=uuid4(),
            phone_number="+919876543219",
            preferred_language=LanguageCode.KANNADA,
            location="Bangalore, Karnataka, India",
            tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        # Create token for regular user
        token_data = create_user_token(regular_user)
        user_token = create_access_token(token_data)
        
        # Try to modify token to claim vendor privileges
        # This is handled by JWT signature validation
        
        # Attempt 1: Try to access vendor-only functionality
        from src.mandi_platform.auth.jwt import get_current_vendor
        from fastapi.security import HTTPAuthorizationCredentials
        from unittest.mock import AsyncMock
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=user_token)
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_vendor(credentials, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Vendor privileges required" in exc_info.value.detail


class TestAuthenticationPerformance:
    """Test performance characteristics of authentication system."""
    
    @pytest.mark.asyncio
    async def test_login_performance(self, async_client: AsyncClient):
        """Test login endpoint performance."""
        import time
        
        test_user = User(
            id=uuid4(),
            phone_number="+919876543220",
            preferred_language=LanguageCode.PUNJABI,
            location="Chandigarh, Punjab, India",
            tech_literacy_level=TechLiteracyLevel.BEGINNER,
            verification_status=VerificationStatus.PHONE_VERIFIED,
            user_type="user"
        )
        
        # Measure login time
        start_time = time.time()
        
        with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
            mock_crud.get_by_phone.return_value = test_user
            mock_crud.update_last_active.return_value = test_user
            
            response = await async_client.post(
                "/auth/login",
                json={"phone_number": "+919876543220"}
            )
        
        end_time = time.time()
        login_time = end_time - start_time
        
        assert response.status_code == 200
        # Login should complete in under 1 second
        assert login_time < 1.0, f"Login too slow: {login_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_token_validation_performance(self, async_client: AsyncClient):
        """Test token validation performance."""
        import time
        
        test_user = User(
            id=uuid4(),
            phone_number="+919876543221",
            preferred_language=LanguageCode.MALAYALAM,
            location="Kochi, Kerala, India",
            tech_literacy_level=TechLiteracyLevel.ADVANCED,
            verification_status=VerificationStatus.FULLY_VERIFIED,
            user_type="user"
        )
        
        # Create token
        token_data = create_user_token(test_user)
        token = create_access_token(token_data)
        
        # Measure token validation time over multiple requests
        start_time = time.time()
        
        for _ in range(10):
            with patch("src.mandi_platform.auth.jwt.user_crud") as mock_crud:
                mock_crud.get.return_value = test_user
                
                response = await async_client.get(
                    "/auth/verify-token",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 10
        
        # Average token validation should be under 0.1 seconds
        assert avg_time < 0.1, f"Token validation too slow: {avg_time:.3f}s average"
    
    @pytest.mark.asyncio
    async def test_concurrent_authentication_performance(self, async_client: AsyncClient):
        """Test performance under concurrent authentication load."""
        import time
        
        test_users = [
            User(
                id=uuid4(),
                phone_number=f"+91987654322{i}",
                preferred_language=LanguageCode.TELUGU,
                location="Hyderabad, Telangana, India",
                tech_literacy_level=TechLiteracyLevel.INTERMEDIATE,
                verification_status=VerificationStatus.PHONE_VERIFIED,
                user_type="user"
            )
            for i in range(10)
        ]
        
        async def concurrent_login(user):
            with patch("src.mandi_platform.api.auth.user_crud") as mock_crud:
                mock_crud.get_by_phone.return_value = user
                mock_crud.update_last_active.return_value = user
                
                return await async_client.post(
                    "/auth/login",
                    json={"phone_number": user.phone_number}
                )
        
        # Measure concurrent login time
        start_time = time.time()
        
        tasks = [concurrent_login(user) for user in test_users]
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # 10 concurrent logins should complete in under 2 seconds
        assert total_time < 2.0, f"Concurrent logins too slow: {total_time:.3f}s"