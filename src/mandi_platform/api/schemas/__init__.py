"""
API schemas package for the Multilingual Mandi Platform.

This package contains Pydantic schemas for request and response models.
"""

from .product import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductResponse,
    ProductListResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    StockUpdateRequest,
    ImageUploadResponse,
    AvailabilityUpdateRequest,
    MultilingualTextSchema,
    LocationSchema,
)

__all__ = [
    "ProductCreateRequest",
    "ProductUpdateRequest",
    "ProductResponse",
    "ProductListResponse",
    "ProductSearchRequest",
    "ProductSearchResponse",
    "StockUpdateRequest",
    "ImageUploadResponse",
    "AvailabilityUpdateRequest",
    "MultilingualTextSchema",
    "LocationSchema",
]
