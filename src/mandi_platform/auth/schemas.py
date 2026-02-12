"""
Authentication schemas for the Multilingual Mandi Platform.

This module defines Pydantic models for authentication requests and responses.
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator
import re


class LoginRequest(BaseModel):
    """Request model for user login."""
    
    phone_number: str = Field(
        ..., 
        description="User's phone number with country code",
        example="+919876543210"
    )
    # For now, we'll use phone number as the primary authentication method
    # In a real system, you might want to add OTP verification
    
    @validator("phone_number")
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove any spaces or special characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Check if it's a valid Indian phone number format
        if not re.match(r'^\+91[6-9]\d{9}$', cleaned):
            raise ValueError("Invalid Indian phone number format. Use +91XXXXXXXXXX")
        
        return cleaned


class LoginResponse(BaseModel):
    """Response model for successful login."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: UUID = Field(..., description="User ID")
    user_type: str = Field(..., description="User type (user or vendor)")
    phone_number: str = Field(..., description="User's phone number")
    preferred_language: str = Field(..., description="User's preferred language")


class Token(BaseModel):
    """JWT token model."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    """Token payload data."""
    
    user_id: UUID = Field(..., description="User ID")
    user_type: str = Field(..., description="User type (user or vendor)")
    phone_number: str = Field(..., description="User's phone number")
    exp: Optional[int] = Field(None, description="Token expiration timestamp")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Request model for user logout."""
    
    # For now, logout will be handled client-side by discarding the token
    # In a more sophisticated system, you might maintain a token blacklist
    pass


class UserRegistrationRequest(BaseModel):
    """Request model for user registration."""
    
    phone_number: str = Field(
        ..., 
        description="User's phone number with country code",
        example="+919876543210"
    )
    preferred_language: str = Field(
        default="hi",
        description="User's preferred language code",
        example="hi"
    )
    location: str = Field(
        ...,
        description="User's location",
        example="Mumbai, Maharashtra, India"
    )
    tech_literacy_level: str = Field(
        default="beginner",
        description="User's technology literacy level",
        example="beginner"
    )
    
    @validator("phone_number")
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove any spaces or special characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Check if it's a valid Indian phone number format
        if not re.match(r'^\+91[6-9]\d{9}$', cleaned):
            raise ValueError("Invalid Indian phone number format. Use +91XXXXXXXXXX")
        
        return cleaned
    
    @validator("preferred_language")
    def validate_language(cls, v):
        """Validate language code."""
        valid_languages = ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
        if v not in valid_languages:
            raise ValueError(f"Language must be one of: {', '.join(valid_languages)}")
        return v
    
    @validator("tech_literacy_level")
    def validate_tech_literacy(cls, v):
        """Validate tech literacy level."""
        valid_levels = ["beginner", "intermediate", "advanced"]
        if v not in valid_levels:
            raise ValueError(f"Tech literacy level must be one of: {', '.join(valid_levels)}")
        return v


class VendorRegistrationRequest(UserRegistrationRequest):
    """Request model for vendor registration."""
    
    business_name: str = Field(
        ...,
        description="Business name",
        example="Sharma Vegetables"
    )
    business_type: str = Field(
        ...,
        description="Type of business",
        example="retailer"
    )
    
    @validator("business_type")
    def validate_business_type(cls, v):
        """Validate business type."""
        valid_types = [
            "individual_trader", "small_business", "cooperative", 
            "wholesaler", "retailer", "farmer", "manufacturer"
        ]
        if v not in valid_types:
            raise ValueError(f"Business type must be one of: {', '.join(valid_types)}")
        return v