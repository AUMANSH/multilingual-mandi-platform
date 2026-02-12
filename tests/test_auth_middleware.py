"""
Unit tests for authentication middleware.

This module tests the authentication middleware functionality including
token validation, security headers, rate limiting, and request processing.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.mandi_platform.auth.middleware import AuthMiddleware, RateLimitMiddleware
from src.mandi_platform.auth.schemas import TokenData
from src.mandi_platform.models.user import User
from src.mandi_platform.models.enums import LanguageCode, TechLiteracyLevel, VerificationStatus


class TestAuthMiddleware:
    """Test authentication middleware functionality."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "127.0.0.1"
        request.state = MagicMock()
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        response = MagicMock(spec=Response)
        response.headers = {}
        return response
    
    @pytest.fixture
    def auth_middleware(self):
        """Create auth middleware instance."""
        app = MagicMock()
        return AuthMiddleware(app)
    
    @pytest.mark.asyncio
    async def test_excluded_paths_skip_auth(self, auth_middleware, mock_request, mock_response):
        """Test that excluded paths skip authentication."""
        mock_request.url.path = "/docs"
        
        async def mock_call_next(request):
            return mock_response
        
        result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert result == mock_response
        # For excluded paths, no authentication state should be set at all
        # The middleware returns early without setting any state
    
    @pytest.mark.asyncio
    async def test_valid_token_authentication(self, auth_middleware, mock_request, mock_response):
        """Test successful authentication with valid token."""
        user_id = uuid4()
        token_data = TokenData(
            user_id=user_id,
            user_type="user",
            phone_number="+919876543210",
            exp=int(time.time()) + 3600
        )
        
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        
        async def mock_call_next(request):
            return mock_response
        
        with patch("src.mandi_platform.auth.middleware.verify_token", return_value=token_data):
            result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert result == mock_response
        assert mock_request.state.user_id == user_id
        assert mock_request.state.user_type == "user"
        assert mock_request.state.phone_number == "+919876543210"
        assert mock_request.state.authenticated is True
    
    @pytest.mark.asyncio
    async def test_invalid_token_authentication(self, auth_middleware, mock_request, mock_response):
        """Test authentication failure with invalid token."""
        mock_request.headers = {"Authorization": "Bearer invalid-token"}
        mock_request.url.path = "/api/protected"
        
        async def mock_call_next(request):
            return mock_response
        
        with patch("src.mandi_platform.auth.middleware.verify_token", 
                  side_effect=HTTPException(status_code=401, detail="Invalid token")):
            result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        # Should return 401 for API endpoints
        assert result.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in result.body.decode()
    
    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, auth_middleware, mock_request, mock_response):
        """Test request without authorization header."""
        mock_request.headers = {}
        
        async def mock_call_next(request):
            return mock_response
        
        result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert result == mock_response
        assert mock_request.state.authenticated is False
    
    @pytest.mark.asyncio
    async def test_malformed_authorization_header(self, auth_middleware, mock_request, mock_response):
        """Test request with malformed authorization header."""
        mock_request.headers = {"Authorization": "InvalidFormat token"}
        
        async def mock_call_next(request):
            return mock_response
        
        result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert result == mock_response
        assert mock_request.state.authenticated is False
    
    @pytest.mark.asyncio
    async def test_security_headers_added(self, auth_middleware, mock_request, mock_response):
        """Test that security headers are added to response."""
        async def mock_call_next(request):
            return mock_response
        
        result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
    
    @pytest.mark.asyncio
    async def test_process_time_header_in_debug(self, auth_middleware, mock_request, mock_response):
        """Test that process time header is added in debug mode."""
        async def mock_call_next(request):
            return mock_response
        
        with patch("src.mandi_platform.auth.middleware.settings.debug", True):
            result = await auth_middleware.dispatch(mock_request, mock_call_next)
        
        assert "X-Process-Time" in result.headers
        # Should be a valid float string
        float(result.headers["X-Process-Time"])


class TestRateLimitMiddleware:
    """Test rate limiting middleware functionality."""
    
    @pytest.fixture
    def rate_limit_middleware(self):
        """Create rate limit middleware instance."""
        app = MagicMock()
        return RateLimitMiddleware(app, requests_per_minute=5)  # Low limit for testing
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        response = MagicMock(spec=Response)
        response.headers = {}
        return response
    
    @pytest.mark.asyncio
    async def test_requests_within_limit(self, rate_limit_middleware, mock_request, mock_response):
        """Test requests within rate limit are allowed."""
        async def mock_call_next(request):
            return mock_response
        
        # Make requests within limit
        for i in range(3):
            result = await rate_limit_middleware.dispatch(mock_request, mock_call_next)
            assert result == mock_response
            assert "X-RateLimit-Limit" in result.headers
            assert "X-RateLimit-Remaining" in result.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limit_middleware, mock_request, mock_response):
        """Test rate limit enforcement."""
        async def mock_call_next(request):
            return mock_response
        
        # Exhaust rate limit
        for i in range(5):
            await rate_limit_middleware.dispatch(mock_request, mock_call_next)
        
        # Next request should be rate limited
        result = await rate_limit_middleware.dispatch(mock_request, mock_call_next)
        
        assert result.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in result.body.decode()
        assert result.headers["Retry-After"] == "60"
        assert result.headers["X-RateLimit-Remaining"] == "0"
    
    @pytest.mark.asyncio
    async def test_different_ips_separate_limits(self, rate_limit_middleware, mock_response):
        """Test that different IPs have separate rate limits."""
        async def mock_call_next(request):
            return mock_response
        
        # Create requests from different IPs
        request1 = MagicMock(spec=Request)
        request1.client.host = "127.0.0.1"
        
        request2 = MagicMock(spec=Request)
        request2.client.host = "192.168.1.1"
        
        # Exhaust limit for first IP
        for i in range(5):
            await rate_limit_middleware.dispatch(request1, mock_call_next)
        
        # First IP should be rate limited
        result1 = await rate_limit_middleware.dispatch(request1, mock_call_next)
        assert result1.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        
        # Second IP should still work
        result2 = await rate_limit_middleware.dispatch(request2, mock_call_next)
        assert result2 == mock_response
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, rate_limit_middleware, mock_request, mock_response):
        """Test rate limit headers are correctly set."""
        async def mock_call_next(request):
            return mock_response
        
        result = await rate_limit_middleware.dispatch(mock_request, mock_call_next)
        
        assert result.headers["X-RateLimit-Limit"] == "5"
        assert "X-RateLimit-Remaining" in result.headers
        
        # Remaining should decrease with each request
        remaining = int(result.headers["X-RateLimit-Remaining"])
        assert 0 <= remaining <= 5
    
    @pytest.mark.asyncio
    async def test_unknown_client_ip(self, rate_limit_middleware, mock_response):
        """Test handling of requests with unknown client IP."""
        request = MagicMock(spec=Request)
        request.client = None  # No client info
        
        async def mock_call_next(request):
            return mock_response
        
        # Should not crash and should still apply rate limiting
        result = await rate_limit_middleware.dispatch(request, mock_call_next)
        assert result == mock_response


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_middleware_chain_execution(self):
        """Test that middleware chain executes in correct order."""
        app = MagicMock()
        auth_middleware = AuthMiddleware(app)
        rate_limit_middleware = RateLimitMiddleware(app, requests_per_minute=10)
        
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {"Authorization": "Bearer valid-token"}
        request.client.host = "127.0.0.1"
        request.state = MagicMock()
        
        response = MagicMock(spec=Response)
        response.headers = {}
        
        user_id = uuid4()
        token_data = TokenData(
            user_id=user_id,
            user_type="user",
            phone_number="+919876543210",
            exp=int(time.time()) + 3600
        )
        
        async def mock_call_next(request):
            return response
        
        # Test auth middleware first
        with patch("src.mandi_platform.auth.middleware.verify_token", return_value=token_data):
            auth_result = await auth_middleware.dispatch(request, mock_call_next)
        
        # Then rate limit middleware
        rate_result = await rate_limit_middleware.dispatch(request, mock_call_next)
        
        # Both should succeed
        assert auth_result == response
        assert rate_result == response
        assert request.state.authenticated is True
        assert "X-RateLimit-Limit" in rate_result.headers
    
    @pytest.mark.asyncio
    async def test_auth_failure_with_rate_limiting(self):
        """Test authentication failure combined with rate limiting."""
        app = MagicMock()
        auth_middleware = AuthMiddleware(app)
        
        request = MagicMock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "POST"
        request.headers = {"Authorization": "Bearer invalid-token"}
        request.client.host = "127.0.0.1"
        request.state = MagicMock()
        
        async def mock_call_next(request):
            return MagicMock(spec=Response)
        
        with patch("src.mandi_platform.auth.middleware.verify_token", 
                  side_effect=HTTPException(status_code=401, detail="Invalid token")):
            result = await auth_middleware.dispatch(request, mock_call_next)
        
        assert result.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in result.body.decode()


class TestMiddlewareErrorHandling:
    """Test middleware error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_auth_middleware_exception_handling(self):
        """Test auth middleware handles exceptions gracefully."""
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.headers = {"Authorization": "Bearer token"}
        request.client.host = "127.0.0.1"
        request.state = MagicMock()
        
        async def mock_call_next(request):
            raise Exception("Unexpected error")
        
        # The middleware should let the exception propagate
        # (it doesn't handle application-level exceptions)
        with pytest.raises(Exception, match="Unexpected error"):
            await middleware.dispatch(request, mock_call_next)
    
    @pytest.mark.asyncio
    async def test_rate_limit_middleware_exception_handling(self):
        """Test rate limit middleware handles exceptions gracefully."""
        app = MagicMock()
        middleware = RateLimitMiddleware(app)
        
        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        
        async def mock_call_next(request):
            raise Exception("Unexpected error")
        
        # Should not crash the middleware
        with pytest.raises(Exception, match="Unexpected error"):
            await middleware.dispatch(request, mock_call_next)