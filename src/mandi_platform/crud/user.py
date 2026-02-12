"""
CRUD operations for User and Vendor models.

This module provides database operations for user management including
creation, retrieval, updates, and specialized vendor operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import CRUDBase
from ..models.user import User, Vendor
from ..models.enums import (
    LanguageCode,
    TechLiteracyLevel,
    VerificationStatus,
    BusinessType,
    MarketReputation,
    PaymentMethod,
    ProductCategory,
)


class UserCRUD(CRUDBase[User, Dict[str, Any], Dict[str, Any]]):
    """CRUD operations for User model."""
    
    async def get_by_phone(self, db: AsyncSession, phone_number: str) -> Optional[User]:
        """Get user by phone number."""
        result = await db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()
    
    async def get_by_language(
        self, 
        db: AsyncSession, 
        language: LanguageCode,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get users by preferred language."""
        result = await db.execute(
            select(User)
            .where(User.preferred_language == language)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_verification_status(
        self,
        db: AsyncSession,
        status: VerificationStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get users by verification status."""
        result = await db.execute(
            select(User)
            .where(User.verification_status == status)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_last_active(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Update user's last active timestamp."""
        user = await self.get(db, user_id)
        if user:
            user.last_active = func.now()
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user
    
    async def search_by_location(
        self,
        db: AsyncSession,
        location_query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Search users by location (case-insensitive partial match)."""
        result = await db.execute(
            select(User)
            .where(User.location.ilike(f"%{location_query}%"))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


class VendorCRUD(CRUDBase[Vendor, Dict[str, Any], Dict[str, Any]]):
    """CRUD operations for Vendor model."""
    
    async def get_by_business_name(
        self, 
        db: AsyncSession, 
        business_name: str
    ) -> Optional[Vendor]:
        """Get vendor by business name."""
        result = await db.execute(
            select(Vendor).where(Vendor.business_name == business_name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_business_type(
        self,
        db: AsyncSession,
        business_type: BusinessType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Vendor]:
        """Get vendors by business type."""
        result = await db.execute(
            select(Vendor)
            .where(Vendor.business_type == business_type)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_rating_range(
        self,
        db: AsyncSession,
        min_rating: Decimal = Decimal('0.0'),
        max_rating: Decimal = Decimal('5.0'),
        skip: int = 0,
        limit: int = 100
    ) -> List[Vendor]:
        """Get vendors within rating range."""
        result = await db.execute(
            select(Vendor)
            .where(and_(
                Vendor.rating >= min_rating,
                Vendor.rating <= max_rating
            ))
            .order_by(Vendor.rating.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_specialization(
        self,
        db: AsyncSession,
        category: ProductCategory,
        skip: int = 0,
        limit: int = 100
    ) -> List[Vendor]:
        """Get vendors by product category specialization."""
        result = await db.execute(
            select(Vendor)
            .where(Vendor.specializations.contains([category.value]))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_trusted_vendors(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Vendor]:
        """Get trusted vendors (high rating, verified, many transactions)."""
        result = await db.execute(
            select(Vendor)
            .where(and_(
                Vendor.rating >= Decimal('4.0'),
                Vendor.total_transactions >= 50,
                Vendor.verification_status == VerificationStatus.FULLY_VERIFIED,
                Vendor.is_verified_business == True
            ))
            .order_by(Vendor.rating.desc(), Vendor.total_transactions.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_location_and_category(
        self,
        db: AsyncSession,
        location_query: str,
        category: ProductCategory,
        skip: int = 0,
        limit: int = 100
    ) -> List[Vendor]:
        """Get vendors by location and specialization."""
        result = await db.execute(
            select(Vendor)
            .where(and_(
                Vendor.location.ilike(f"%{location_query}%"),
                Vendor.specializations.contains([category.value])
            ))
            .order_by(Vendor.rating.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_rating(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        new_rating: Decimal,
        transaction_count: int = 1
    ) -> Optional[Vendor]:
        """Update vendor rating using weighted average."""
        vendor = await self.get(db, vendor_id)
        if vendor:
            vendor.update_rating(new_rating, transaction_count)
            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)
        return vendor
    
    async def add_specialization(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        category: ProductCategory
    ) -> Optional[Vendor]:
        """Add specialization to vendor."""
        vendor = await self.get(db, vendor_id)
        if vendor:
            vendor.add_specialization(category)
            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)
        return vendor
    
    async def remove_specialization(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        category: ProductCategory
    ) -> Optional[Vendor]:
        """Remove specialization from vendor."""
        vendor = await self.get(db, vendor_id)
        if vendor:
            vendor.remove_specialization(category)
            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)
        return vendor
    
    async def add_payment_method(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        method: PaymentMethod
    ) -> Optional[Vendor]:
        """Add payment method to vendor."""
        vendor = await self.get(db, vendor_id)
        if vendor:
            vendor.add_payment_method(method)
            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)
        return vendor
    
    async def remove_payment_method(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        method: PaymentMethod
    ) -> Optional[Vendor]:
        """Remove payment method from vendor."""
        vendor = await self.get(db, vendor_id)
        if vendor:
            vendor.remove_payment_method(method)
            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)
        return vendor
    
    async def get_vendor_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get overall vendor statistics."""
        total_vendors = await db.execute(select(func.count(Vendor.id)))
        avg_rating = await db.execute(select(func.avg(Vendor.rating)))
        total_transactions = await db.execute(select(func.sum(Vendor.total_transactions)))
        
        verified_vendors = await db.execute(
            select(func.count(Vendor.id))
            .where(Vendor.verification_status == VerificationStatus.FULLY_VERIFIED)
        )
        
        trusted_vendors = await db.execute(
            select(func.count(Vendor.id))
            .where(and_(
                Vendor.rating >= Decimal('4.0'),
                Vendor.total_transactions >= 50,
                Vendor.is_verified_business == True
            ))
        )
        
        return {
            "total_vendors": total_vendors.scalar() or 0,
            "average_rating": float(avg_rating.scalar() or 0),
            "total_transactions": total_transactions.scalar() or 0,
            "verified_vendors": verified_vendors.scalar() or 0,
            "trusted_vendors": trusted_vendors.scalar() or 0,
        }


# Create instances for use in the application
user_crud = UserCRUD(User)
vendor_crud = VendorCRUD(Vendor)