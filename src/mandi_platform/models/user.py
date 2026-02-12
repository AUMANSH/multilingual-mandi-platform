"""
User and Vendor models for the Multilingual Mandi Platform.

This module defines the core user models including User and Vendor entities
with all required fields and relationships.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    Integer,
    Numeric,
    Text,
    ForeignKey,
    Boolean,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .enums import (
    LanguageCode,
    TechLiteracyLevel,
    VerificationStatus,
    BusinessType,
    MarketReputation,
    PaymentMethod,
    ProductCategory,
)


class User(Base):
    """
    Base user model for the platform.
    
    Represents both buyers and vendors with common user attributes.
    Vendors extend this model with additional business-specific fields.
    """
    __tablename__ = 'users'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core user information
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    preferred_language = Column(Enum(LanguageCode), nullable=False, default=LanguageCode.HINDI)
    
    # Location information (stored as JSON-like string for flexibility)
    # Format: "City, State, Country" or coordinates
    location = Column(Text, nullable=False)
    
    # User characteristics
    tech_literacy_level = Column(
        Enum(TechLiteracyLevel), 
        nullable=False, 
        default=TechLiteracyLevel.BEGINNER
    )
    verification_status = Column(
        Enum(VerificationStatus), 
        nullable=False, 
        default=VerificationStatus.UNVERIFIED
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # User type discriminator for inheritance
    user_type = Column(String(20), nullable=False, default='user')
    
    # Polymorphic identity
    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': user_type,
        'with_polymorphic': '*'
    }
    
    def __init__(self, **kwargs):
        """Initialize user with defaults."""
        # Set defaults if not provided
        if 'preferred_language' not in kwargs:
            kwargs['preferred_language'] = LanguageCode.HINDI
        if 'tech_literacy_level' not in kwargs:
            kwargs['tech_literacy_level'] = TechLiteracyLevel.BEGINNER
        if 'verification_status' not in kwargs:
            kwargs['verification_status'] = VerificationStatus.UNVERIFIED
        if 'user_type' not in kwargs:
            kwargs['user_type'] = 'user'
        
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone_number}, lang={self.preferred_language})>"


class Vendor(User):
    """
    Vendor model extending User with business-specific attributes.
    
    Represents sellers/traders on the platform with additional business
    information, ratings, and transaction history.
    """
    __tablename__ = 'vendors'
    
    # Foreign key to parent User
    id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    
    # Business information
    business_name = Column(String(255), nullable=False)
    business_type = Column(Enum(BusinessType), nullable=False)
    
    # Business performance metrics
    rating = Column(Numeric(3, 2), default=Decimal('0.00'), nullable=False)
    total_transactions = Column(Integer, default=0, nullable=False)
    market_reputation = Column(
        Enum(MarketReputation), 
        nullable=False, 
        default=MarketReputation.NEW
    )
    
    # Business verification
    is_verified_business = Column(Boolean, default=False, nullable=False)
    business_registration_number = Column(String(50), nullable=True)
    
    # Store specializations and payment methods as JSON arrays
    specializations = Column(JSON, default=list, nullable=False)
    payment_methods = Column(JSON, default=list, nullable=False)
    
    # Polymorphic identity
    __mapper_args__ = {
        'polymorphic_identity': 'vendor'
    }
    
    def __init__(self, **kwargs):
        """Initialize vendor with defaults."""
        # Set vendor-specific defaults if not provided
        if 'rating' not in kwargs:
            kwargs['rating'] = Decimal('0.00')
        if 'total_transactions' not in kwargs:
            kwargs['total_transactions'] = 0
        if 'market_reputation' not in kwargs:
            kwargs['market_reputation'] = MarketReputation.NEW
        if 'is_verified_business' not in kwargs:
            kwargs['is_verified_business'] = False
        if 'specializations' not in kwargs:
            kwargs['specializations'] = []
        if 'payment_methods' not in kwargs:
            kwargs['payment_methods'] = []
        if 'user_type' not in kwargs:
            kwargs['user_type'] = 'vendor'
        
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<Vendor(id={self.id}, business={self.business_name}, rating={self.rating})>"
    
    def update_rating(self, new_rating: Decimal, transaction_count: int = 1) -> None:
        """
        Update vendor rating using weighted average.
        
        Args:
            new_rating: New rating to incorporate (0.00 to 5.00)
            transaction_count: Number of transactions this rating represents
        """
        if self.total_transactions == 0:
            self.rating = new_rating
        else:
            # Weighted average calculation
            total_weight = self.total_transactions + transaction_count
            calculated_rating = (
                (self.rating * self.total_transactions + new_rating * transaction_count) 
                / total_weight
            )
            # Round to 2 decimal places for security and consistency
            self.rating = calculated_rating.quantize(Decimal('0.01'))
        
        self.total_transactions += transaction_count
    
    def add_specialization(self, category: ProductCategory) -> None:
        """Add a product category specialization."""
        if self.specializations is None:
            self.specializations = []
        if category.value not in self.specializations:
            self.specializations.append(category.value)
    
    def remove_specialization(self, category: ProductCategory) -> None:
        """Remove a product category specialization."""
        if self.specializations and category.value in self.specializations:
            self.specializations.remove(category.value)
    
    def add_payment_method(self, method: PaymentMethod) -> None:
        """Add a supported payment method."""
        if self.payment_methods is None:
            self.payment_methods = []
        if method.value not in self.payment_methods:
            self.payment_methods.append(method.value)
    
    def remove_payment_method(self, method: PaymentMethod) -> None:
        """Remove a supported payment method."""
        if self.payment_methods and method.value in self.payment_methods:
            self.payment_methods.remove(method.value)
    
    def get_specializations(self) -> List[ProductCategory]:
        """Get specializations as ProductCategory enums."""
        if not self.specializations:
            return []
        return [ProductCategory(spec) for spec in self.specializations]
    
    def get_payment_methods(self) -> List[PaymentMethod]:
        """Get payment methods as PaymentMethod enums."""
        if not self.payment_methods:
            return []
        return [PaymentMethod(method) for method in self.payment_methods]
    
    @property
    def is_trusted_vendor(self) -> bool:
        """Check if vendor meets trusted criteria."""
        return (
            self.rating >= Decimal('4.0') and 
            self.total_transactions >= 50 and
            self.verification_status == VerificationStatus.FULLY_VERIFIED and
            self.is_verified_business
        )
    
    @property
    def reputation_score(self) -> int:
        """Calculate overall reputation score (0-100)."""
        base_score = min(float(self.rating) * 20, 100)  # Rating contributes 0-100
        transaction_bonus = min(self.total_transactions / 10, 20)  # Up to 20 bonus points
        verification_bonus = 0
        
        if self.verification_status == VerificationStatus.FULLY_VERIFIED:
            verification_bonus += 10
        if self.is_verified_business:
            verification_bonus += 10
        
        return min(int(base_score + transaction_bonus + verification_bonus), 100)