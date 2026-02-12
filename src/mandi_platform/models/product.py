"""
Product and ProductCategory models for the Multilingual Mandi Platform.

This module defines the product catalog models including Product, ProductCategory,
and related entities with multilingual support and Elasticsearch integration.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

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
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .enums import (
    LanguageCode,
    ProductCategory as ProductCategoryEnum,
    QualityGrade,
    MeasurementUnit,
    AvailabilityStatus,
    SeasonalPattern,
    ProductCondition,
    PriceSource,
    MarketConditions,
)


class MultilingualText:
    """Helper class for multilingual text fields."""
    
    def __init__(self, text_dict: Optional[Dict[str, str]] = None):
        """Initialize with text dictionary."""
        self.text_dict = text_dict or {}
    
    def get_text(self, language: LanguageCode, fallback: LanguageCode = LanguageCode.ENGLISH) -> str:
        """Get text in specified language with fallback."""
        return self.text_dict.get(language.value, self.text_dict.get(fallback.value, ""))
    
    def set_text(self, language: LanguageCode, text: str) -> None:
        """Set text for a specific language."""
        self.text_dict[language.value] = text
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON storage."""
        return self.text_dict.copy()
    
    @classmethod
    def from_dict(cls, text_dict: Dict[str, str]) -> 'MultilingualText':
        """Create from dictionary."""
        return cls(text_dict)


class ProductCategoryModel(Base):
    """
    Product category model for organizing products.
    
    Represents hierarchical product categories with multilingual names
    and descriptions.
    """
    __tablename__ = 'product_categories'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Category information
    category_enum = Column(Enum(ProductCategoryEnum), nullable=False, unique=True)
    
    # Multilingual names and descriptions (stored as JSON)
    names = Column(JSON, nullable=False, default=dict)
    descriptions = Column(JSON, nullable=False, default=dict)
    
    # Hierarchy support
    parent_id = Column(UUID(as_uuid=True), ForeignKey('product_categories.id'), nullable=True)
    parent = relationship("ProductCategoryModel", remote_side=[id], backref="subcategories")
    
    # Category metadata
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    products = relationship("Product", back_populates="category_model")
    
    def __init__(self, **kwargs):
        """Initialize category with defaults."""
        if 'names' not in kwargs:
            kwargs['names'] = {}
        if 'descriptions' not in kwargs:
            kwargs['descriptions'] = {}
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'sort_order' not in kwargs:
            kwargs['sort_order'] = 0
        
        super().__init__(**kwargs)
    
    def get_name(self, language: LanguageCode = LanguageCode.ENGLISH) -> str:
        """Get category name in specified language."""
        multilingual_name = MultilingualText.from_dict(self.names or {})
        return multilingual_name.get_text(language)
    
    def set_name(self, language: LanguageCode, name: str) -> None:
        """Set category name for a specific language."""
        if self.names is None:
            self.names = {}
        self.names[language.value] = name
    
    def get_description(self, language: LanguageCode = LanguageCode.ENGLISH) -> str:
        """Get category description in specified language."""
        multilingual_desc = MultilingualText.from_dict(self.descriptions or {})
        return multilingual_desc.get_text(language)
    
    def set_description(self, language: LanguageCode, description: str) -> None:
        """Set category description for a specific language."""
        if self.descriptions is None:
            self.descriptions = {}
        self.descriptions[language.value] = description
    
    def __repr__(self) -> str:
        return f"<ProductCategory(id={self.id}, enum={self.category_enum})>"


class Product(Base):
    """
    Product model for the marketplace.
    
    Represents products with multilingual support, pricing, availability,
    and Elasticsearch integration for search functionality.
    """
    __tablename__ = 'products'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Vendor relationship
    vendor_id = Column(UUID(as_uuid=True), ForeignKey('vendors.id'), nullable=False)
    vendor = relationship("Vendor", backref="products")
    
    # Category relationship
    category_id = Column(UUID(as_uuid=True), ForeignKey('product_categories.id'), nullable=False)
    category_model = relationship("ProductCategoryModel", back_populates="products")
    
    # Basic product information
    sku = Column(String(100), unique=True, nullable=True, index=True)  # Stock Keeping Unit
    
    # Multilingual product information (stored as JSON)
    names = Column(JSON, nullable=False, default=dict)
    descriptions = Column(JSON, nullable=False, default=dict)
    
    # Pricing information
    base_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    
    # Product specifications
    unit = Column(Enum(MeasurementUnit), nullable=False)
    minimum_order_quantity = Column(Numeric(10, 2), default=Decimal('1'), nullable=False)
    maximum_order_quantity = Column(Numeric(10, 2), nullable=True)
    
    # Quality and condition
    quality_grade = Column(Enum(QualityGrade), nullable=False, default=QualityGrade.STANDARD)
    condition = Column(Enum(ProductCondition), nullable=False, default=ProductCondition.NEW)
    
    # Availability
    availability_status = Column(Enum(AvailabilityStatus), nullable=False, default=AvailabilityStatus.AVAILABLE)
    stock_quantity = Column(Numeric(10, 2), nullable=True)
    seasonal_pattern = Column(Enum(SeasonalPattern), nullable=False, default=SeasonalPattern.YEAR_ROUND)
    
    # Location information (stored as JSON for flexibility)
    location = Column(JSON, nullable=False)
    
    # Product media
    images = Column(JSON, default=list, nullable=False)  # List of image URLs
    videos = Column(JSON, default=list, nullable=False)  # List of video URLs
    
    # Product attributes (flexible JSON storage for category-specific attributes)
    attributes = Column(JSON, default=dict, nullable=False)
    
    # SEO and search optimization
    search_keywords = Column(JSON, default=list, nullable=False)  # List of keywords
    tags = Column(JSON, default=list, nullable=False)  # List of tags
    
    # Product status
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Elasticsearch sync tracking
    elasticsearch_synced_at = Column(DateTime(timezone=True), nullable=True)
    elasticsearch_sync_version = Column(Integer, default=1, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_product_vendor_category', 'vendor_id', 'category_id'),
        Index('idx_product_availability', 'availability_status', 'is_active'),
        Index('idx_product_price_range', 'base_price', 'quality_grade'),
        Index('idx_product_location', 'location'),  # GIN index for JSON
        Index('idx_product_search', 'search_keywords'),  # GIN index for JSON
    )
    
    def __init__(self, **kwargs):
        """Initialize product with defaults."""
        if 'names' not in kwargs:
            kwargs['names'] = {}
        if 'descriptions' not in kwargs:
            kwargs['descriptions'] = {}
        if 'location' not in kwargs:
            kwargs['location'] = {}
        if 'images' not in kwargs:
            kwargs['images'] = []
        if 'videos' not in kwargs:
            kwargs['videos'] = []
        if 'attributes' not in kwargs:
            kwargs['attributes'] = {}
        if 'search_keywords' not in kwargs:
            kwargs['search_keywords'] = []
        if 'tags' not in kwargs:
            kwargs['tags'] = []
        if 'currency' not in kwargs:
            kwargs['currency'] = "INR"
        if 'minimum_order_quantity' not in kwargs:
            kwargs['minimum_order_quantity'] = Decimal('1')
        if 'quality_grade' not in kwargs:
            kwargs['quality_grade'] = QualityGrade.STANDARD
        if 'condition' not in kwargs:
            kwargs['condition'] = ProductCondition.NEW
        if 'availability_status' not in kwargs:
            kwargs['availability_status'] = AvailabilityStatus.AVAILABLE
        if 'seasonal_pattern' not in kwargs:
            kwargs['seasonal_pattern'] = SeasonalPattern.YEAR_ROUND
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'is_featured' not in kwargs:
            kwargs['is_featured'] = False
        if 'elasticsearch_sync_version' not in kwargs:
            kwargs['elasticsearch_sync_version'] = 1
        
        super().__init__(**kwargs)
    
    def get_name(self, language: LanguageCode = LanguageCode.ENGLISH) -> str:
        """Get product name in specified language."""
        multilingual_name = MultilingualText.from_dict(self.names or {})
        return multilingual_name.get_text(language)
    
    def set_name(self, language: LanguageCode, name: str) -> None:
        """Set product name for a specific language."""
        if self.names is None:
            self.names = {}
        self.names[language.value] = name
        self._mark_for_elasticsearch_sync()
    
    def get_description(self, language: LanguageCode = LanguageCode.ENGLISH) -> str:
        """Get product description in specified language."""
        multilingual_desc = MultilingualText.from_dict(self.descriptions or {})
        return multilingual_desc.get_text(language)
    
    def set_description(self, language: LanguageCode, description: str) -> None:
        """Set product description for a specific language."""
        if self.descriptions is None:
            self.descriptions = {}
        self.descriptions[language.value] = description
        self._mark_for_elasticsearch_sync()
    
    def add_image(self, image_url: str) -> None:
        """Add an image URL to the product."""
        if self.images is None:
            self.images = []
        if image_url not in self.images:
            self.images.append(image_url)
            self._mark_for_elasticsearch_sync()
    
    def remove_image(self, image_url: str) -> None:
        """Remove an image URL from the product."""
        if self.images and image_url in self.images:
            self.images.remove(image_url)
            self._mark_for_elasticsearch_sync()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the product."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
            self._mark_for_elasticsearch_sync()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the product."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            self._mark_for_elasticsearch_sync()
    
    def add_search_keyword(self, keyword: str) -> None:
        """Add a search keyword to the product."""
        if self.search_keywords is None:
            self.search_keywords = []
        if keyword not in self.search_keywords:
            self.search_keywords.append(keyword)
            self._mark_for_elasticsearch_sync()
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a product attribute."""
        if self.attributes is None:
            self.attributes = {}
        self.attributes[key] = value
        self._mark_for_elasticsearch_sync()
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a product attribute."""
        if self.attributes is None:
            return default
        return self.attributes.get(key, default)
    
    def update_stock(self, new_quantity: Decimal) -> None:
        """Update stock quantity and availability status."""
        self.stock_quantity = new_quantity
        
        # Auto-update availability based on stock
        if new_quantity <= 0:
            self.availability_status = AvailabilityStatus.OUT_OF_STOCK
        elif new_quantity <= 10:  # Configurable threshold
            self.availability_status = AvailabilityStatus.LIMITED_STOCK
        else:
            self.availability_status = AvailabilityStatus.AVAILABLE
        
        self._mark_for_elasticsearch_sync()
    
    def _mark_for_elasticsearch_sync(self) -> None:
        """Mark product for Elasticsearch synchronization."""
        self.elasticsearch_sync_version += 1
        self.elasticsearch_synced_at = None
    
    def to_elasticsearch_document(self) -> Dict[str, Any]:
        """Convert product to Elasticsearch document format."""
        return {
            "id": str(self.id),
            "vendor_id": str(self.vendor_id),
            "category_id": str(self.category_id),
            "sku": self.sku,
            "names": self.names or {},
            "descriptions": self.descriptions or {},
            "base_price": float(self.base_price),
            "currency": self.currency,
            "unit": self.unit.value,
            "minimum_order_quantity": float(self.minimum_order_quantity),
            "maximum_order_quantity": float(self.maximum_order_quantity) if self.maximum_order_quantity else None,
            "quality_grade": self.quality_grade.value,
            "condition": self.condition.value,
            "availability_status": self.availability_status.value,
            "stock_quantity": float(self.stock_quantity) if self.stock_quantity else None,
            "seasonal_pattern": self.seasonal_pattern.value,
            "location": self.location or {},
            "images": self.images or [],
            "videos": self.videos or [],
            "attributes": self.attributes or {},
            "search_keywords": self.search_keywords or [],
            "tags": self.tags or [],
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "sync_version": self.elasticsearch_sync_version,
        }
    
    @property
    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return (
            self.is_active and 
            self.availability_status in [AvailabilityStatus.AVAILABLE, AvailabilityStatus.LIMITED_STOCK]
        )
    
    @property
    def display_price(self) -> str:
        """Get formatted display price."""
        return f"₹{self.base_price:.2f} per {self.unit.value}"
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.get_name()}, price={self.base_price})>"


class PriceHistory(Base):
    """
    Price history model for tracking product price changes over time.
    
    Stores historical pricing data for analytics and trend analysis.
    """
    __tablename__ = 'price_history'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Product relationship
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=False)
    product = relationship("Product", backref="price_history")
    
    # Price information
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    
    # Context information
    quality_grade = Column(Enum(QualityGrade), nullable=False)
    location = Column(JSON, nullable=False)  # Location where price was recorded
    source = Column(Enum(PriceSource), nullable=False)
    market_conditions = Column(Enum(MarketConditions), nullable=False, default=MarketConditions.NORMAL)
    
    # Additional context
    quantity_range = Column(String(50), nullable=True)  # e.g., "1-10 kg", "bulk"
    notes = Column(Text, nullable=True)
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_price_history_product_date', 'product_id', 'recorded_at'),
        Index('idx_price_history_location_date', 'location', 'recorded_at'),
        Index('idx_price_history_source', 'source', 'recorded_at'),
    )
    
    def __init__(self, **kwargs):
        """Initialize price history with defaults."""
        if 'currency' not in kwargs:
            kwargs['currency'] = "INR"
        if 'market_conditions' not in kwargs:
            kwargs['market_conditions'] = MarketConditions.NORMAL
        if 'recorded_at' not in kwargs:
            kwargs['recorded_at'] = datetime.utcnow()
        
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, date={self.recorded_at})>"