"""
Authentication API endpoints for the Multilingual Mandi Platform.

This module provides REST API endpoints for user authentication including
login, logout, registration, and token management.
"""

from datetime import timedelta
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database import get_db_session
from ..models.user import User, Vendor
from ..models.enums import LanguageCode, TechLiteracyLevel, VerificationStatus, BusinessType
from ..crud.user import user_crud, vendor_crud
from ..auth.schemas import (
    LoginRequest, 
    LoginResponse, 
    UserRegistrationRequest,
    VendorRegistrationRequest,
    Token,
    LogoutRequest,
)
from ..auth.jwt import create_access_token, create_user_token, get_token_expires_in
from ..auth.dependencies import require_auth, require_vendor_auth
from ..config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
) -> LoginResponse:
    """
    Authenticate user and return JWT token.
    
    This endpoint authenticates users based on their phone number.
    In a production system, you would typically implement OTP verification
    or other secure authentication methods.
    
    Args:
        login_request: Login credentials
        db: Database session
        
    Returns:
        JWT token and user information
        
    Raises:
        HTTPException: If authentication fails
    """
    logger.info(
        "Login attempt",
        phone_number=login_request.phone_number,
    )
    
    # Find user by phone number
    user = await user_crud.get_by_phone(db, login_request.phone_number)
    
    if not user:
        logger.warning(
            "Login failed - user not found",
            phone_number=login_request.phone_number,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number. Please register first.",
        )
    
    # Create JWT token
    token_data = create_user_token(user)
    access_token = create_access_token(token_data)
    
    # Update last active timestamp
    await user_crud.update_last_active(db, user.id)
    
    logger.info(
        "Login successful",
        user_id=str(user.id),
        user_type=user.user_type,
        phone_number=user.phone_number,
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=get_token_expires_in(),
        user_id=user.id,
        user_type=user.user_type,
        phone_number=user.phone_number,
        preferred_language=user.preferred_language.value,
    )


@router.post("/register", response_model=LoginResponse)
async def register_user(
    registration_request: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db_session)
) -> LoginResponse:
    """
    Register a new user and return JWT token.
    
    Args:
        registration_request: User registration data
        db: Database session
        
    Returns:
        JWT token and user information
        
    Raises:
        HTTPException: If registration fails
    """
    logger.info(
        "User registration attempt",
        phone_number=registration_request.phone_number,
    )
    
    # Check if user already exists
    existing_user = await user_crud.get_by_phone(db, registration_request.phone_number)
    if existing_user:
        logger.warning(
            "Registration failed - user already exists",
            phone_number=registration_request.phone_number,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this phone number already exists. Please login instead.",
        )
    
    # Create new user
    user_data = {
        "phone_number": registration_request.phone_number,
        "preferred_language": LanguageCode(registration_request.preferred_language),
        "location": registration_request.location,
        "tech_literacy_level": TechLiteracyLevel(registration_request.tech_literacy_level),
        "verification_status": VerificationStatus.UNVERIFIED,
        "user_type": "user",
    }
    
    user = await user_crud.create(db, user_data)
    
    # Create JWT token
    token_data = create_user_token(user)
    access_token = create_access_token(token_data)
    
    logger.info(
        "User registration successful",
        user_id=str(user.id),
        phone_number=user.phone_number,
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=get_token_expires_in(),
        user_id=user.id,
        user_type=user.user_type,
        phone_number=user.phone_number,
        preferred_language=user.preferred_language.value,
    )


@router.post("/register-vendor", response_model=LoginResponse)
async def register_vendor(
    registration_request: VendorRegistrationRequest,
    db: AsyncSession = Depends(get_db_session)
) -> LoginResponse:
    """
    Register a new vendor and return JWT token.
    
    Args:
        registration_request: Vendor registration data
        db: Database session
        
    Returns:
        JWT token and vendor information
        
    Raises:
        HTTPException: If registration fails
    """
    logger.info(
        "Vendor registration attempt",
        phone_number=registration_request.phone_number,
        business_name=registration_request.business_name,
    )
    
    # Check if user already exists
    existing_user = await user_crud.get_by_phone(db, registration_request.phone_number)
    if existing_user:
        logger.warning(
            "Vendor registration failed - user already exists",
            phone_number=registration_request.phone_number,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this phone number already exists. Please login instead.",
        )
    
    # Check if business name is already taken
    existing_vendor = await vendor_crud.get_by_business_name(db, registration_request.business_name)
    if existing_vendor:
        logger.warning(
            "Vendor registration failed - business name already exists",
            business_name=registration_request.business_name,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business name already exists. Please choose a different name.",
        )
    
    # Create new vendor
    vendor_data = {
        "phone_number": registration_request.phone_number,
        "preferred_language": LanguageCode(registration_request.preferred_language),
        "location": registration_request.location,
        "tech_literacy_level": TechLiteracyLevel(registration_request.tech_literacy_level),
        "verification_status": VerificationStatus.UNVERIFIED,
        "user_type": "vendor",
        "business_name": registration_request.business_name,
        "business_type": BusinessType(registration_request.business_type),
    }
    
    vendor = await vendor_crud.create(db, vendor_data)
    
    # Create JWT token
    token_data = create_user_token(vendor)
    access_token = create_access_token(token_data)
    
    logger.info(
        "Vendor registration successful",
        user_id=str(vendor.id),
        phone_number=vendor.phone_number,
        business_name=vendor.business_name,
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=get_token_expires_in(),
        user_id=vendor.id,
        user_type=vendor.user_type,
        phone_number=vendor.phone_number,
        preferred_language=vendor.preferred_language.value,
    )


@router.post("/logout")
async def logout(
    logout_request: LogoutRequest,
    current_user: User = Depends(require_auth)
) -> Dict[str, str]:
    """
    Logout current user.
    
    In this implementation, logout is handled client-side by discarding the token.
    In a more sophisticated system, you might maintain a token blacklist in Redis.
    
    Args:
        logout_request: Logout request (currently empty)
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    logger.info(
        "User logout",
        user_id=str(current_user.id),
        user_type=current_user.user_type,
    )
    
    # In a production system, you might want to:
    # 1. Add the token to a blacklist in Redis
    # 2. Update user's last_active timestamp
    # 3. Clear any user-specific cache data
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: User = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    user_info = {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "preferred_language": current_user.preferred_language.value,
        "location": current_user.location,
        "tech_literacy_level": current_user.tech_literacy_level.value,
        "verification_status": current_user.verification_status.value,
        "user_type": current_user.user_type,
        "created_at": current_user.created_at,
        "last_active": current_user.last_active,
    }
    
    # Add vendor-specific information if user is a vendor
    if isinstance(current_user, Vendor):
        user_info.update({
            "business_name": current_user.business_name,
            "business_type": current_user.business_type.value,
            "rating": float(current_user.rating),
            "total_transactions": current_user.total_transactions,
            "market_reputation": current_user.market_reputation.value,
            "is_verified_business": current_user.is_verified_business,
            "specializations": current_user.specializations,
            "payment_methods": current_user.payment_methods,
            "is_trusted_vendor": current_user.is_trusted_vendor,
            "reputation_score": current_user.reputation_score,
        })
    
    return user_info


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(require_auth)
) -> Token:
    """
    Refresh JWT token for current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        New JWT token
    """
    logger.info(
        "Token refresh",
        user_id=str(current_user.id),
        user_type=current_user.user_type,
    )
    
    # Create new JWT token
    token_data = create_user_token(current_user)
    access_token = create_access_token(token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/verify-token")
async def verify_token_endpoint(
    current_user: User = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Verify if current token is valid.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Token validation result
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "user_type": current_user.user_type,
        "phone_number": current_user.phone_number,
    }