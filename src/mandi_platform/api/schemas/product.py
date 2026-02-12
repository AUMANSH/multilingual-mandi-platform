"""
Pydantic schemas for product API endpoints.

This module defines request and response models for product management
with multilingual support and validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from ...models.enums import (
    LanguageCode,
    ProductCategory,
    QualityGrade,
    MeasurementUnit,
    AvailabilityStatus,
    SeasonalPattern,
    ProductCondition,
)


class MultilingualTextSchema(BaseModel):
    """Schema for multilingual text fields."""
    hi: Optional[str] = None
    en: Optional[str] = None
    ta: Optional[str] = None
    te: Optional[str] = None
    bn: Optional[str] = None
    mr: Optional[str] = None
    gu: Optional[str] = None
    kn: Optional[str] = None
    ml: Optional[str] = None
    pa: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "en": "Fresh Tomatoes",
                "hi": "ताजा टमाटर",
                "ta": "புதிய தக்காளி"
            }
        }


class LocationSchema(BaseModel):
    """Schema for location information."""
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "pincode": "400001"
            }
        }


class ProductCreateRequest(BaseModel):
    """Request schema for creating a new product."""
    category_id: UUID
    names: Dict[str, str] = Field(..., description="Product names in multiple languages")
    descriptions: Dict[str, str] = Field(..., description="Product descriptions in multiple languages")
    base_price: Decimal = Field(..., gt=0, description="Base price in INR")
    unit: str = Field(..., description="Measurement unit")
    minimum_order_quantity: Decimal = Field(default=Decimal('1'), gt=0)
    maximum_order_quantity: Optional[Decimal] = Field(default=None, gt=0)
    quality_grade: str = Field(default=QualityGrade.STANDARD.value)
    condition: str = Field(default=ProductCondition.NEW.value)
    availability_status: str = Field(default=AvailabilityStatus.AVAILABLE.value)
    stock_quantity: Optional[Decimal] = Field(default=None, ge=0)
    seasonal_pattern: str = Field(default=SeasonalPattern.YEAR_ROUND.value)
    location: Dict[str, Any] = Field(..., description="Product location")
    images: List[str] = Field(default_factory=list)
    videos: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    search_keywords: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sku: Optional[str] = None
    is_featured: bool = False
    
    @validator('names', 'descriptions')
    def validate_multilingual_text(cls, v):
        """Ensure at least one language is provided."""
        if not v or not any(v.values()):
            raise ValueError("At least one language translation must be provided")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "category_id": "123e4567-e89b-12d3-a456-426614174000",
                "names": {
                    "en": "Fresh Tomatoes",
                    "hi": "ताजा टमाटर"
                },
                "descriptions": {
                    "en": "Fresh red tomatoes from local farms",
                    "hi": "स्थानीय खेतों से ताजा लाल टमाटर"
                },
                "base_price": 40.00,
                "unit": "kg",
                "quality_grade": "standard",
                "location": {
                    "city": "Mumbai",
                    "state": "Maharashtra"
                },
                "stock_quantity": 100.0,
                "tags": ["fresh", "vegetables", "local"]
            }
        }


class ProductUpdateRequest(BaseModel):
    """Request schema for updating a product."""
    names: Optional[Dict[str, str]] = None
    descriptions: Optional[Dict[str, str]] = None
    base_price: Optional[Decimal] = Field(default=None, gt=0)
    unit: Optional[str] = None
    minimum_order_quantity: Optional[Decimal] = Field(default=None, gt=0)
    maximum_order_quantity: Optional[Decimal] = Field(default=None, gt=0)
    quality_grade: Optional[str] = None
    condition: Optional[str] = None
    availability_status: Optional[str] = None
    stock_quantity: Optional[Decimal] = Field(default=None, ge=0)
    seasonal_pattern: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    search_keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    
    class Config:
        schema_extra = {
            "example": {
                "base_price": 45.00,
                "stock_quantity": 80.0,
                "availability_status": "limited_stock"
            }
        }


class ProductResponse(BaseModel):
    """Response schema for product information."""
    id: UUID
    vendor_id: UUID
    category_id: UUID
    sku: Optional[str]
    names: Dict[str, str]
    descriptions: Dict[str, str]
    base_price: Decimal
    currency: str
    unit: str
    minimum_order_quantity: Decimal
    maximum_order_quantity: Optional[Decimal]
    quality_grade: str
    condition: str
    availability_status: str
    stock_quantity: Optional[Decimal]
    seasonal_pattern: str
    location: Dict[str, Any]
    images: List[str]
    videos: List[str]
    attributes: Dict[str, Any]
    search_keywords: List[str]
    tags: List[str]
    is_active: bool
    is_featured: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "vendor_id": "123e4567-e89b-12d3-a456-426614174001",
                "category_id": "123e4567-e89b-12d3-a456-426614174002",
                "sku": "TOM-001",
                "names": {
                    "en": "Fresh Tomatoes",
                    "hi": "ताजा टमाटर"
                },
                "descriptions": {
                    "en": "Fresh red tomatoes from local farms",
                    "hi": "स्थानीय खेतों से ताजा लाल टमाटर"
                },
                "base_price": 40.00,
                "currency": "INR",
                "unit": "kg",
                "minimum_order_quantity": 1.0,
                "maximum_order_quantity": None,
                "quality_grade": "standard",
                "condition": "new",
                "availability_status": "available",
                "stock_quantity": 100.0,
                "seasonal_pattern": "year_round",
                "location": {
                    "city": "Mumbai",
                    "state": "Maharashtra"
                },
                "images": ["https://example.com/tomato1.jpg"],
                "videos": [],
                "attributes": {},
                "search_keywords": ["tomato", "vegetable"],
                "tags": ["fresh", "vegetables", "local"],
                "is_active": True,
                "is_featured": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class ProductListResponse(BaseModel):
    """Response schema for product list."""
    products: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ProductSearchRequest(BaseModel):
    """Request schema for product search."""
    query: str = Field(default="", description="Search query text")
    language: str = Field(default=LanguageCode.ENGLISH.value)
    category_id: Optional[UUID] = None
    min_price: Optional[Decimal] = Field(default=None, ge=0)
    max_price: Optional[Decimal] = Field(default=None, ge=0)
    quality_grades: Optional[List[str]] = None
    availability_statuses: Optional[List[str]] = None
    location: Optional[Dict[str, Any]] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="relevance")
    include_alternatives: bool = True
    boost_local: bool = True
    
    class Config:
        schema_extra = {
            "example": {
                "query": "tomatoes",
                "language": "en",
                "min_price": 30.0,
                "max_price": 50.0,
                "quality_grades": ["standard", "premium"],
                "page": 1,
                "page_size": 20
            }
        }


class ProductSearchResponse(BaseModel):
    """Response schema for product search results."""
    products: List[Dict[str, Any]]
    out_of_stock: List[Dict[str, Any]]
    alternatives: List[Dict[str, Any]]
    suggestions: List[str]
    facets: Dict[str, Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    search_metadata: Dict[str, Any]


class StockUpdateRequest(BaseModel):
    """Request schema for updating product stock."""
    stock_quantity: Decimal = Field(..., ge=0, description="New stock quantity")
    
    class Config:
        schema_extra = {
            "example": {
                "stock_quantity": 75.0
            }
        }


class ImageUploadResponse(BaseModel):
    """Response schema for image upload."""
    image_url: str
    product_id: UUID
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "image_url": "https://example.com/products/image123.jpg",
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Image uploaded successfully"
            }
        }


class AvailabilityUpdateRequest(BaseModel):
    """Request schema for updating product availability."""
    availability_status: str = Field(..., description="New availability status")
    stock_quantity: Optional[Decimal] = Field(default=None, ge=0)
    
    @validator('availability_status')
    def validate_availability_status(cls, v):
        """Validate availability status."""
        valid_statuses = [status.value for status in AvailabilityStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid availability status. Must be one of: {valid_statuses}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "availability_status": "limited_stock",
                "stock_quantity": 10.0
            }
        }
