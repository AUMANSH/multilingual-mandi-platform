"""
Authentication middleware for the Multilingual Mandi Platform.

This module provides middleware for handling authentication and security headers.
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ..config import settings
from .jwt import verify_token

logger = structlog.get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that validates JWT tokens and adds user context.
    
    This middleware:
    1. Extracts JWT tokens from Authorization headers
    2. Validates tokens and adds user context to request state
    3. Handles authentication errors gracefully
    4. Logs authentication events for security monitoring
    """
    
    def __init__(self, app, exclude_paths: Optional[list[str]] = None):
        """
        Initialize authentication middleware.
        
        Args:
            app: FastAPI application instance
            exclude_paths: List of paths to exclude from authentication
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/register-vendor",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through authentication middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        start_time = time.time()
        
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        
        if authorization and scheme.lower() == "bearer" and token:
            try:
                # Verify token and add user context to request state
                token_data = verify_token(token)
                request.state.user_id = token_data.user_id
                request.state.user_type = token_data.user_type
                request.state.phone_number = token_data.phone_number
                request.state.authenticated = True
                
                logger.info(
                    "Authentication successful",
                    user_id=str(token_data.user_id),
                    user_type=token_data.user_type,
                    path=request.url.path,
                    method=request.method,
                )
                
            except HTTPException as e:
                # Log authentication failure
                logger.warning(
                    "Authentication failed",
                    error=e.detail,
                    path=request.url.path,
                    method=request.method,
                    client_ip=request.client.host if request.client else None,
                )
                
                # For API endpoints, return 401
                if request.url.path.startswith("/api/"):
                    return Response(
                        content='{"detail": "Authentication required"}',
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={"WWW-Authenticate": "Bearer"},
                        media_type="application/json",
                    )
                
                # For other endpoints, let the handler decide
                request.state.authenticated = False
        else:
            request.state.authenticated = False
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Add processing time header in debug mode
        if settings.debug:
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    
    This is a simple in-memory rate limiter. In production, you would
    want to use Redis or another distributed cache for rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            requests_per_minute: Maximum requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiting middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            HTTP response
        """
        client_ip = request.client.host if request.client else "unknown"
        current_time = int(time.time() / 60)  # Current minute
        
        # Clean old entries (simple cleanup)
        self.request_counts = {
            key: count for key, count in self.request_counts.items()
            if key[1] >= current_time - 1
        }
        
        # Check rate limit
        key = (client_ip, current_time)
        current_requests = self.request_counts.get(key, 0)
        
        if current_requests >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests=current_requests,
                limit=self.requests_per_minute,
            )
            
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
                media_type="application/json",
            )
        
        # Increment request count
        self.request_counts[key] = current_requests + 1
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - self.request_counts[key])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response