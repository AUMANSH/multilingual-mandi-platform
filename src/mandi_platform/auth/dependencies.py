"""
Authentication dependencies for the Multilingual Mandi Platform.

This module provides FastAPI dependencies for authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from ..models.user import User, Vendor
from .jwt import get_current_user, get_current_vendor, get_current_active_user, get_current_active_vendor


def require_auth(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency that requires user authentication.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current authenticated User object
        
    Raises:
        HTTPException: If user is not authenticated
    """
    return current_user


def require_vendor_auth(
    current_vendor: Vendor = Depends(get_current_active_vendor)
) -> Vendor:
    """
    Dependency that requires vendor authentication.
    
    Args:
        current_vendor: Current authenticated vendor
        
    Returns:
        Current authenticated Vendor object
        
    Raises:
        HTTPException: If user is not authenticated or not a vendor
    """
    return current_vendor


def optional_auth(
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    """
    Dependency that provides optional authentication.
    
    Args:
        current_user: Current authenticated user (if any)
        
    Returns:
        Current authenticated User object or None
    """
    return current_user


def require_verified_user(
    current_user: User = Depends(require_auth)
) -> User:
    """
    Dependency that requires a verified user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current verified User object
        
    Raises:
        HTTPException: If user is not verified
    """
    from ..models.enums import VerificationStatus
    
    if current_user.verification_status == VerificationStatus.UNVERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account verification required. Please verify your phone number.",
        )
    
    return current_user


def require_verified_vendor(
    current_vendor: Vendor = Depends(require_vendor_auth)
) -> Vendor:
    """
    Dependency that requires a verified vendor.
    
    Args:
        current_vendor: Current authenticated vendor
        
    Returns:
        Current verified Vendor object
        
    Raises:
        HTTPException: If vendor is not verified
    """
    from ..models.enums import VerificationStatus
    
    if current_vendor.verification_status == VerificationStatus.UNVERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor verification required. Please complete your verification process.",
        )
    
    return current_vendor


def require_trusted_vendor(
    current_vendor: Vendor = Depends(require_verified_vendor)
) -> Vendor:
    """
    Dependency that requires a trusted vendor.
    
    Args:
        current_vendor: Current authenticated vendor
        
    Returns:
        Current trusted Vendor object
        
    Raises:
        HTTPException: If vendor is not trusted
    """
    if not current_vendor.is_trusted_vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trusted vendor status required. Improve your rating and complete more transactions.",
        )
    
    return current_vendor


class RoleChecker:
    """
    Role-based access control checker.
    
    This class can be used to create dependencies that check for specific roles
    or permissions.
    """
    
    def __init__(self, allowed_roles: list[str]):
        """
        Initialize role checker.
        
        Args:
            allowed_roles: List of allowed user types/roles
        """
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if current user has required role.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current authenticated User object
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        if current_user.user_type not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}",
            )
        
        return current_user


# Pre-defined role checkers
require_user_role = RoleChecker(["user"])
require_vendor_role = RoleChecker(["vendor"])
require_any_role = RoleChecker(["user", "vendor"])