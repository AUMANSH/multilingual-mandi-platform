"""
JWT token utilities for the Multilingual Mandi Platform.

This module provides functions for creating, validating, and managing JWT tokens
for user authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from uuid import UUID

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db_session
from ..models.user import User, Vendor
from ..crud.user import user_crud, vendor_crud
from .schemas import TokenData

# Security scheme for extracting Bearer tokens
security = HTTPBearer()


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing token payload data
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object with decoded payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        
        user_id: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        phone_number: str = payload.get("phone_number")
        exp: int = payload.get("exp")
        
        if user_id is None or user_type is None or phone_number is None:
            raise credentials_exception
        
        # Validate UUID format
        try:
            parsed_user_id = UUID(user_id)
        except (ValueError, TypeError):
            raise credentials_exception
            
        token_data = TokenData(
            user_id=parsed_user_id,
            user_type=user_type,
            phone_number=phone_number,
            exp=exp
        )
        
        return token_data
        
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current authenticated User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token_data = verify_token(credentials.credentials)
    
    user = await user_crud.get(db, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_vendor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Vendor:
    """
    Get the current authenticated vendor from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current authenticated Vendor object
        
    Raises:
        HTTPException: If token is invalid, user not found, or user is not a vendor
    """
    token_data = verify_token(credentials.credentials)
    
    # Check if the user type in token is vendor
    if token_data.user_type != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Vendor privileges required.",
        )
    
    vendor = await vendor_crud.get(db, token_data.user_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vendor not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return vendor


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user (additional validation can be added here).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active User object
        
    Raises:
        HTTPException: If user is inactive or suspended
    """
    # Add any additional user status checks here
    # For example, check if user is suspended, banned, etc.
    
    return current_user


async def get_current_active_vendor(
    current_vendor: Vendor = Depends(get_current_vendor)
) -> Vendor:
    """
    Get the current active vendor (additional validation can be added here).
    
    Args:
        current_vendor: Current authenticated vendor
        
    Returns:
        Current active Vendor object
        
    Raises:
        HTTPException: If vendor is inactive or suspended
    """
    # Add any additional vendor status checks here
    # For example, check if vendor is suspended, banned, etc.
    
    return current_vendor


def create_user_token(user: User) -> dict:
    """
    Create token payload for a user.
    
    Args:
        user: User object
        
    Returns:
        Dictionary containing token payload data
    """
    return {
        "sub": str(user.id),
        "user_type": user.user_type,
        "phone_number": user.phone_number,
        "preferred_language": user.preferred_language.value,
    }


def get_token_expires_in() -> int:
    """
    Get token expiration time in seconds.
    
    Returns:
        Token expiration time in seconds
    """
    return settings.access_token_expire_minutes * 60