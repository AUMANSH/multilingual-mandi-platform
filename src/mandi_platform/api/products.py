"""
Product management API endpoints for the Multilingual Mandi Platform.

This module provides REST API endpoints for product listing, search, filtering,
and management with multilingual support.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database import get_db_session
from ..models.user import User, Vendor
from ..models.product import Product
from ..models.enums import LanguageCode, QualityGrade, AvailabilityStatus
from ..crud.product import ProductCRUD
from ..auth.dependencies import require_auth, require_vendor_auth
from .schemas.product import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductResponse,
    ProductListResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    StockUpdateRequest,
    ImageUploadResponse,
    AvailabilityUpdateRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category_id: Optional[UUID] = Query(default=None, description="Filter by category"),
    vendor_id: Optional[UUID] = Query(default=None, description="Filter by vendor"),
    active_only: bool = Query(default=True, description="Show only active products"),
    db: AsyncSession = Depends(get_db_session),
) -> ProductListResponse:
    """
    List products with pagination and filtering.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        category_id: Optional category filter
        vendor_id: Optional vendor filter
        active_only: Show only active products
        db: Database session
        
    Returns:
        Paginated list of products
    """
    logger.info(
        "Listing products",
        page=page,
        page_size=page_size,
        category_id=str(category_id) if category_id else None,
        vendor_id=str(vendor_id) if vendor_id else None,
    )
    
    crud = ProductCRUD(db)
    offset = (page - 1) * page_size
    
    # Get products based on filters
    if vendor_id:
        products = await crud.get_products_by_vendor(
            vendor_id, active_only=active_only, limit=page_size, offset=offset
        )
    elif category_id:
        products = await crud.get_products_by_category(
            category_id, active_only=active_only, limit=page_size, offset=offset
        )
    else:
        # Get all products (implement in CRUD if needed)
        products = []
    
    # Convert to response models
    product_responses = [
        ProductResponse.from_orm(product) for product in products
    ]
    
    # Calculate pagination metadata
    total = len(products)  # This should be a count query in production
    total_pages = (total + page_size - 1) // page_size
    
    return ProductListResponse(
        products=product_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/products/search", response_model=ProductSearchResponse)
async def search_products(
    search_request: ProductSearchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ProductSearchResponse:
    """
    Search products with multilingual support and advanced filtering.
    
    Args:
        search_request: Search parameters
        db: Database session
        
    Returns:
        Search results with products, alternatives, and suggestions
    """
    logger.info(
        "Searching products",
        query=search_request.query,
        language=search_request.language,
        page=search_request.page,
    )
    
    crud = ProductCRUD(db)
    
    # Build filters
    filters = {}
    if search_request.category_id:
        filters["category_id"] = str(search_request.category_id)
    
    # Build price range
    price_range = None
    if search_request.min_price is not None or search_request.max_price is not None:
        price_range = (
            search_request.min_price or Decimal('0'),
            search_request.max_price or Decimal('999999')
        )
    
    # Convert quality grades and availability statuses
    quality_grades = None
    if search_request.quality_grades:
        quality_grades = [QualityGrade(qg) for qg in search_request.quality_grades]
    
    availability_statuses = None
    if search_request.availability_statuses:
        availability_statuses = [AvailabilityStatus(av) for av in search_request.availability_statuses]
    
    # Perform search
    results = await crud.search_products(
        query=search_request.query,
        language=LanguageCode(search_request.language),
        filters=filters,
        location=search_request.location,
        price_range=price_range,
        quality_grades=quality_grades,
        availability_statuses=availability_statuses,
        page=search_request.page,
        page_size=search_request.page_size,
        sort_by=search_request.sort_by,
        include_alternatives=search_request.include_alternatives,
        boost_local=search_request.boost_local,
    )
    
    return ProductSearchResponse(**results)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Get a single product by ID.
    
    Args:
        product_id: Product UUID
        db: Database session
        
    Returns:
        Product details
        
    Raises:
        HTTPException: If product not found
    """
    logger.info("Getting product", product_id=str(product_id))
    
    crud = ProductCRUD(db)
    product = await crud.get_product(product_id)
    
    if not product:
        logger.warning("Product not found", product_id=str(product_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    return ProductResponse.from_orm(product)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_request: ProductCreateRequest,
    current_vendor: Vendor = Depends(require_vendor_auth),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Create a new product (vendor only).
    
    Args:
        product_request: Product creation data
        current_vendor: Current authenticated vendor
        db: Database session
        
    Returns:
        Created product
        
    Raises:
        HTTPException: If creation fails
    """
    logger.info(
        "Creating product",
        vendor_id=str(current_vendor.id),
        category_id=str(product_request.category_id),
    )
    
    crud = ProductCRUD(db)
    
    # Create product
    product = await crud.create_product(
        vendor_id=current_vendor.id,
        category_id=product_request.category_id,
        names=product_request.names,
        descriptions=product_request.descriptions,
        base_price=product_request.base_price,
        unit=product_request.unit,
        quality_grade=product_request.quality_grade,
        location=product_request.location,
        minimum_order_quantity=product_request.minimum_order_quantity,
        maximum_order_quantity=product_request.maximum_order_quantity,
        condition=product_request.condition,
        availability_status=product_request.availability_status,
        stock_quantity=product_request.stock_quantity,
        seasonal_pattern=product_request.seasonal_pattern,
        images=product_request.images,
        videos=product_request.videos,
        attributes=product_request.attributes,
        search_keywords=product_request.search_keywords,
        tags=product_request.tags,
        sku=product_request.sku,
        is_featured=product_request.is_featured,
    )
    
    if not product:
        logger.error("Failed to create product", vendor_id=str(current_vendor.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )
    
    logger.info("Product created successfully", product_id=str(product.id))
    return ProductResponse.from_orm(product)


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_request: ProductUpdateRequest,
    current_vendor: Vendor = Depends(require_vendor_auth),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Update a product (vendor only, own products).
    
    Args:
        product_id: Product UUID
        product_request: Product update data
        current_vendor: Current authenticated vendor
        db: Database session
        
    Returns:
        Updated product
        
    Raises:
        HTTPException: If product not found or unauthorized
    """
    logger.info(
        "Updating product",
        product_id=str(product_id),
        vendor_id=str(current_vendor.id),
    )
    
    crud = ProductCRUD(db)
    
    # Check if product exists and belongs to vendor
    product = await crud.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if product.vendor_id != current_vendor.id:
        logger.warning(
            "Unauthorized product update attempt",
            product_id=str(product_id),
            vendor_id=str(current_vendor.id),
            product_vendor_id=str(product.vendor_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )
    
    # Update product
    updates = product_request.dict(exclude_unset=True)
    updated_product = await crud.update_product(product_id, **updates)
    
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )
    
    logger.info("Product updated successfully", product_id=str(product_id))
    return ProductResponse.from_orm(updated_product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    current_vendor: Vendor = Depends(require_vendor_auth),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete a product (vendor only, own products).
    
    This performs a soft delete by marking the product as inactive.
    
    Args:
        product_id: Product UUID
        current_vendor: Current authenticated vendor
        db: Database session
        
    Raises:
        HTTPException: If product not found or unauthorized
    """
    logger.info(
        "Deleting product",
        product_id=str(product_id),
        vendor_id=str(current_vendor.id),
    )
    
    crud = ProductCRUD(db)
    
    # Check if product exists and belongs to vendor
    product = await crud.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if product.vendor_id != current_vendor.id:
        logger.warning(
            "Unauthorized product deletion attempt",
            product_id=str(product_id),
            vendor_id=str(current_vendor.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own products"
        )
    
    # Delete product (soft delete)
    success = await crud.delete_product(product_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )
    
    logger.info("Product deleted successfully", product_id=str(product_id))


@router.put("/products/{product_id}/availability", response_model=ProductResponse)
async def update_product_availability(
    product_id: UUID,
    availability_request: AvailabilityUpdateRequest,
    current_vendor: Vendor = Depends(require_vendor_auth),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Update product availability status (vendor only, own products).
    
    Args:
        product_id: Product UUID
        availability_request: Availability update data
        current_vendor: Current authenticated vendor
        db: Database session
        
    Returns:
        Updated product
        
    Raises:
        HTTPException: If product not found or unauthorized
    """
    logger.info(
        "Updating product availability",
        product_id=str(product_id),
        vendor_id=str(current_vendor.id),
        new_status=availability_request.availability_status,
    )
    
    crud = ProductCRUD(db)
    
    # Check if product exists and belongs to vendor
    product = await crud.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if product.vendor_id != current_vendor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )
    
    # Update availability
    updates = {"availability_status": availability_request.availability_status}
    if availability_request.stock_quantity is not None:
        updates["stock_quantity"] = availability_request.stock_quantity
    
    updated_product = await crud.update_product(product_id, **updates)
    
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product availability"
        )
    
    logger.info("Product availability updated successfully", product_id=str(product_id))
    return ProductResponse.from_orm(updated_product)


@router.put("/products/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    product_id: UUID,
    stock_request: StockUpdateRequest,
    current_vendor: Vendor = Depends(require_vendor_auth),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """
    Update product stock quantity (vendor only, own products).
    
    This automatically updates availability status based on stock levels.
    
    Args:
        product_id: Product UUID
        stock_request: Stock update data
        current_vendor: Current authenticated vendor
        db: Database session
        
    Returns:
        Updated product
        
    Raises:
        HTTPException: If product not found or unauthorized
    """
    logger.info(
        "Updating product stock",
        product_id=str(product_id),
        vendor_id=str(current_vendor.id),
        new_quantity=float(stock_request.stock_quantity),
    )
    
    crud = ProductCRUD(db)
    
    # Check if product exists and belongs to vendor
    product = await crud.get_product(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    
    if product.vendor_id != current_vendor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )
    
    # Update stock (this also updates availability status automatically)
    updated_product = await crud.update_stock(product_id, stock_request.stock_quantity)
    
    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product stock"
        )
    
    logger.info("Product stock updated successfully", product_id=str(product_id))
    return ProductResponse.from_orm(updated_product)


@router.get("/products/featured", response_model=List[ProductResponse])
async def get_featured_products(
    limit: int = Query(default=10, ge=1, le=50, description="Number of featured products"),
    category_id: Optional[UUID] = Query(default=None, description="Filter by category"),
    db: AsyncSession = Depends(get_db_session),
) -> List[ProductResponse]:
    """
    Get featured products.
    
    Args:
        limit: Maximum number of products to return
        category_id: Optional category filter
        db: Database session
        
    Returns:
        List of featured products
    """
    logger.info("Getting featured products", limit=limit, category_id=str(category_id) if category_id else None)
    
    crud = ProductCRUD(db)
    products = await crud.get_featured_products(limit=limit, category_id=category_id)
    
    return [ProductResponse.from_orm(product) for product in products]


@router.get("/vendors/{vendor_id}/products", response_model=ProductListResponse)
async def get_vendor_products(
    vendor_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db_session),
) -> ProductListResponse:
    """
    Get all products for a specific vendor.
    
    Args:
        vendor_id: Vendor UUID
        page: Page number
        page_size: Items per page
        active_only: Show only active products
        db: Database session
        
    Returns:
        Paginated list of vendor's products
    """
    logger.info("Getting vendor products", vendor_id=str(vendor_id), page=page)
    
    crud = ProductCRUD(db)
    offset = (page - 1) * page_size
    
    products = await crud.get_products_by_vendor(
        vendor_id, active_only=active_only, limit=page_size, offset=offset
    )
    
    product_responses = [ProductResponse.from_orm(product) for product in products]
    
    total = len(products)
    total_pages = (total + page_size - 1) // page_size
    
    return ProductListResponse(
        products=product_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/products/low-stock", response_model=List[ProductResponse])
async def get_low_stock_products(
    threshold: Decimal = Query(default=Decimal('10'), ge=0, description="Stock threshold"),
    current_vendor: Vendor = Depends(require_vendor_auth),
    db: AsyncSession = Depends(get_db_session),
) -> List[ProductResponse]:
    """
    Get vendor's products with low stock (vendor only).
    
    Args:
        threshold: Stock quantity threshold
        current_vendor: Current authenticated vendor
        db: Database session
        
    Returns:
        List of low stock products
    """
    logger.info(
        "Getting low stock products",
        vendor_id=str(current_vendor.id),
        threshold=float(threshold),
    )
    
    crud = ProductCRUD(db)
    products = await crud.get_low_stock_products(
        vendor_id=current_vendor.id,
        threshold=threshold
    )
    
    return [ProductResponse.from_orm(product) for product in products]
