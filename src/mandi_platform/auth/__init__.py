"""
Authentication module for the Multilingual Mandi Platform.

This module provides JWT-based authentication with role-based access control
for users and vendors.
"""

from .jwt import create_access_token, verify_token, get_current_user, get_current_vendor
from .middleware import AuthMiddleware
from .schemas import Token, TokenData, LoginRequest, LoginResponse
from .dependencies import require_auth, require_vendor_auth

__all__ = [
    "create_access_token",
    "verify_token", 
    "get_current_user",
    "get_current_vendor",
    "AuthMiddleware",
    "Token",
    "TokenData", 
    "LoginRequest",
    "LoginResponse",
    "require_auth",
    "require_vendor_auth",
]