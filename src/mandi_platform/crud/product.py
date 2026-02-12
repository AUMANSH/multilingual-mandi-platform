"""
CRUD operations for Product and ProductCategory models.

This module provides database operations for product management
with Elasticsearch synchronization.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.product import Product, ProductCategoryModel, PriceHistory
from ..models.enums import (
    LanguageCode,
    ProductCategory,
    QualityGrade,
    AvailabilityStatus,
    SeasonalPattern,
    ProductCondition,
    PriceSource,
    MarketConditions,
)
from ..search.product_search import ProductSearchService

logger = logging.getLogger(__name__)


class ProductCRUD:
    """CRUD operations for Product model."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.search_service = ProductSearchService()
    
    async def create_product(
        self,
        vendor_id: UUID,
        category_id: UUID,
        names: Dict[str, str],
        descriptions: Dict[str, str],
        base_price: Decimal,
        unit: str,
        quality_grade: str = QualityGrade.STANDARD.value,
        location: Dict[str, Any] = None,
        **kwargs
    ) -> Optional[Product]:
        """Create a new product."""
        try:
            product_data = {
                "vendor_id": vendor_id,
                "category_id": category_id,
                "names": names,
                "descriptions": descriptions,
                "base_price": base_price,
                "unit": unit,
                "quality_grade": quality_grade,
                "location": location or {},
                **kwargs
            }
            
            product = Product(**product_data)
            self.db.add(product)
            await self.db.flush()  # Get the ID without committing
            
            # Index in Elasticsearch
            await self._sync_to_elasticsearch(product)
            
            await self.db.commit()
            await self.db.refresh(product)
            
            logger.info(f"Created product {product.id}")
            return product
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating product: {e}")
            return None
    
    async def get_product(self, product_id: UUID) -> Optional[Product]:
        """Get a product by ID."""
        try:
            stmt = select(Product).where(Product.id == product_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None
    
    async def get_product_with_vendor(self, product_id: UUID) -> Optional[Product]:
        """Get a product with vendor information."""
        try:
            stmt = (
                select(Product)
                .options(selectinload(Product.vendor))
                .where(Product.id == product_id)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting product with vendor {product_id}: {e}")
            return None
    
    async def get_products_by_vendor(
        self,
        vendor_id: UUID,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Product]:
        """Get products by vendor ID."""
        try:
            stmt = select(Product).where(Product.vendor_id == vendor_id)
            
            if active_only:
                stmt = stmt.where(Product.is_active == True)
            
            stmt = stmt.limit(limit).offset(offset).order_by(Product.created_at.desc())
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting products for vendor {vendor_id}: {e}")
            return []
    
    async def get_products_by_category(
        self,
        category_id: UUID,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Product]:
        """Get products by category ID."""
        try:
            stmt = select(Product).where(Product.category_id == category_id)
            
            if active_only:
                stmt = stmt.where(Product.is_active == True)
            
            stmt = stmt.limit(limit).offset(offset).order_by(Product.created_at.desc())
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting products for category {category_id}: {e}")
            return []
    
    async def update_product(
        self,
        product_id: UUID,
        **updates
    ) -> Optional[Product]:
        """Update a product."""
        try:
            # Get the existing product
            product = await self.get_product(product_id)
            if not product:
                return None
            
            # Update fields
            for key, value in updates.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            
            # Mark for Elasticsearch sync
            product._mark_for_elasticsearch_sync()
            
            await self.db.commit()
            await self.db.refresh(product)
            
            # Sync to Elasticsearch
            await self._sync_to_elasticsearch(product)
            
            logger.info(f"Updated product {product_id}")
            return product
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating product {product_id}: {e}")
            return None
    
    async def delete_product(self, product_id: UUID) -> bool:
        """Soft delete a product (mark as inactive)."""
        try:
            stmt = (
                update(Product)
                .where(Product.id == product_id)
                .values(is_active=False)
            )
            
            result = await self.db.execute(stmt)
            
            if result.rowcount > 0:
                await self.db.commit()
                
                # Remove from Elasticsearch
                await self.search_service.delete_product(str(product_id))
                
                logger.info(f"Soft deleted product {product_id}")
                return True
            
            return False
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting product {product_id}: {e}")
            return False
    
    async def update_stock(
        self,
        product_id: UUID,
        new_quantity: Decimal
    ) -> Optional[Product]:
        """Update product stock quantity."""
        try:
            product = await self.get_product(product_id)
            if not product:
                return None
            
            product.update_stock(new_quantity)
            
            await self.db.commit()
            await self.db.refresh(product)
            
            # Sync to Elasticsearch
            await self._sync_to_elasticsearch(product)
            
            logger.info(f"Updated stock for product {product_id} to {new_quantity}")
            return product
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating stock for product {product_id}: {e}")
            return None
    
    async def search_products(
        self,
        query: str = "",
        language: LanguageCode = LanguageCode.ENGLISH,
        filters: Optional[Dict[str, Any]] = None,
        **search_params
    ) -> Dict[str, Any]:
        """Search products using Elasticsearch."""
        try:
            return await self.search_service.search_products(
                query=query,
                language=language,
                filters=filters,
                **search_params
            )
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return {
                "products": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
                "error": str(e)
            }
    
    async def get_featured_products(
        self,
        limit: int = 10,
        category_id: Optional[UUID] = None
    ) -> List[Product]:
        """Get featured products."""
        try:
            stmt = select(Product).where(
                and_(
                    Product.is_active == True,
                    Product.is_featured == True
                )
            )
            
            if category_id:
                stmt = stmt.where(Product.category_id == category_id)
            
            stmt = stmt.limit(limit).order_by(Product.created_at.desc())
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting featured products: {e}")
            return []
    
    async def get_low_stock_products(
        self,
        vendor_id: Optional[UUID] = None,
        threshold: Decimal = Decimal('10')
    ) -> List[Product]:
        """Get products with low stock."""
        try:
            stmt = select(Product).where(
                and_(
                    Product.is_active == True,
                    Product.stock_quantity <= threshold,
                    Product.stock_quantity > 0
                )
            )
            
            if vendor_id:
                stmt = stmt.where(Product.vendor_id == vendor_id)
            
            stmt = stmt.order_by(Product.stock_quantity.asc())
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            return []
    
    async def _sync_to_elasticsearch(self, product: Product) -> bool:
        """Sync product to Elasticsearch."""
        try:
            doc = product.to_elasticsearch_document()
            success = await self.search_service.index_product(doc)
            
            if success:
                # Update sync timestamp
                product.elasticsearch_synced_at = func.now()
                await self.db.commit()
            
            return success
        except Exception as e:
            logger.error(f"Error syncing product {product.id} to Elasticsearch: {e}")
            return False


class ProductCategoryCRUD:
    """CRUD operations for ProductCategory model."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
    
    async def create_category(
        self,
        category_enum: ProductCategory,
        names: Dict[str, str],
        descriptions: Dict[str, str] = None,
        parent_id: Optional[UUID] = None
    ) -> Optional[ProductCategoryModel]:
        """Create a new product category."""
        try:
            category_data = {
                "category_enum": category_enum,
                "names": names,
                "descriptions": descriptions or {},
                "parent_id": parent_id,
            }
            
            category = ProductCategoryModel(**category_data)
            self.db.add(category)
            await self.db.commit()
            await self.db.refresh(category)
            
            logger.info(f"Created category {category.id}")
            return category
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating category: {e}")
            return None
    
    async def get_category(self, category_id: UUID) -> Optional[ProductCategoryModel]:
        """Get a category by ID."""
        try:
            stmt = select(ProductCategoryModel).where(ProductCategoryModel.id == category_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting category {category_id}: {e}")
            return None
    
    async def get_category_by_enum(
        self,
        category_enum: ProductCategory
    ) -> Optional[ProductCategoryModel]:
        """Get a category by enum value."""
        try:
            stmt = select(ProductCategoryModel).where(
                ProductCategoryModel.category_enum == category_enum
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting category by enum {category_enum}: {e}")
            return None
    
    async def get_all_categories(
        self,
        active_only: bool = True,
        parent_id: Optional[UUID] = None
    ) -> List[ProductCategoryModel]:
        """Get all categories, optionally filtered by parent."""
        try:
            stmt = select(ProductCategoryModel)
            
            if active_only:
                stmt = stmt.where(ProductCategoryModel.is_active == True)
            
            if parent_id is not None:
                stmt = stmt.where(ProductCategoryModel.parent_id == parent_id)
            
            stmt = stmt.order_by(ProductCategoryModel.sort_order, ProductCategoryModel.category_enum)
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    async def update_category(
        self,
        category_id: UUID,
        **updates
    ) -> Optional[ProductCategoryModel]:
        """Update a category."""
        try:
            category = await self.get_category(category_id)
            if not category:
                return None
            
            for key, value in updates.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            
            await self.db.commit()
            await self.db.refresh(category)
            
            logger.info(f"Updated category {category_id}")
            return category
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating category {category_id}: {e}")
            return None


class PriceHistoryCRUD:
    """CRUD operations for PriceHistory model."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
    
    async def record_price(
        self,
        product_id: UUID,
        price: Decimal,
        quality_grade: QualityGrade,
        location: Dict[str, Any],
        source: PriceSource,
        market_conditions: MarketConditions = MarketConditions.NORMAL,
        **kwargs
    ) -> Optional[PriceHistory]:
        """Record a price point in history."""
        try:
            price_data = {
                "product_id": product_id,
                "price": price,
                "quality_grade": quality_grade,
                "location": location,
                "source": source,
                "market_conditions": market_conditions,
                **kwargs
            }
            
            price_history = PriceHistory(**price_data)
            self.db.add(price_history)
            await self.db.commit()
            await self.db.refresh(price_history)
            
            logger.debug(f"Recorded price history for product {product_id}")
            return price_history
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording price history: {e}")
            return None
    
    async def get_price_history(
        self,
        product_id: UUID,
        days: int = 30,
        limit: int = 100
    ) -> List[PriceHistory]:
        """Get price history for a product."""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            stmt = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.product_id == product_id,
                        PriceHistory.recorded_at >= cutoff_date
                    )
                )
                .order_by(PriceHistory.recorded_at.desc())
                .limit(limit)
            )
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting price history for product {product_id}: {e}")
            return []
    
    async def get_average_price(
        self,
        product_id: UUID,
        days: int = 7,
        quality_grade: Optional[QualityGrade] = None
    ) -> Optional[Decimal]:
        """Get average price for a product over specified days."""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(func.avg(PriceHistory.price)).where(
                and_(
                    PriceHistory.product_id == product_id,
                    PriceHistory.recorded_at >= cutoff_date
                )
            )
            
            if quality_grade:
                stmt = stmt.where(PriceHistory.quality_grade == quality_grade)
            
            result = await self.db.execute(stmt)
            avg_price = result.scalar()
            
            return Decimal(str(avg_price)) if avg_price else None
        except Exception as e:
            logger.error(f"Error getting average price for product {product_id}: {e}")
            return None