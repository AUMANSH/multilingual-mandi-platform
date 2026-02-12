"""
Product search service using Elasticsearch.

This module provides comprehensive product search functionality with
multilingual support, filtering, ranking, and recommendation capabilities.
"""

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
import logging
from datetime import datetime, timedelta

from ..elasticsearch_client import get_elasticsearch_manager
from ..models.enums import LanguageCode, AvailabilityStatus, QualityGrade

logger = logging.getLogger(__name__)


class ProductRecommendationEngine:
    """Engine for generating product recommendations."""
    
    def __init__(self, es_manager):
        self.es_manager = es_manager
        self.index_name = "products"
    
    async def get_similar_products(
        self,
        product_id: str,
        limit: int = 5,
        exclude_out_of_stock: bool = True
    ) -> List[Dict[str, Any]]:
        """Get products similar to the given product."""
        try:
            # First get the source product
            source_product = await self.es_manager.get_document(
                self.index_name, product_id
            )
            
            if not source_product:
                return []
            
            # Build similarity query with enhanced scoring
            search_query = {
                "bool": {
                    "must": [
                        {"term": {"is_active": True}}
                    ],
                    "should": [
                        # Category match (highest priority)
                        {
                            "term": {
                                "category_id": {
                                    "value": source_product.get("category_id"),
                                    "boost": 5.0
                                }
                            }
                        },
                        # Tags similarity
                        {
                            "terms": {
                                "tags": source_product.get("tags", []),
                                "boost": 3.0
                            }
                        },
                        # Price range similarity (±30%)
                        {
                            "range": {
                                "base_price": {
                                    "gte": source_product.get("base_price", 0) * 0.7,
                                    "lte": source_product.get("base_price", 0) * 1.3,
                                    "boost": 2.0
                                }
                            }
                        },
                        # Quality grade match
                        {
                            "term": {
                                "quality_grade": {
                                    "value": source_product.get("quality_grade"),
                                    "boost": 2.5
                                }
                            }
                        },
                        # Location proximity (same state)
                        {
                            "term": {
                                "location.state": {
                                    "value": source_product.get("location", {}).get("state"),
                                    "boost": 1.5
                                }
                            }
                        },
                        # Search keywords overlap
                        {
                            "terms": {
                                "search_keywords": source_product.get("search_keywords", []),
                                "boost": 1.8
                            }
                        }
                    ],
                    "must_not": [
                        {"term": {"id": product_id}}  # Exclude the source product
                    ],
                    "minimum_should_match": 1
                }
            }
            
            # Exclude out-of-stock if requested
            if exclude_out_of_stock:
                search_query["bool"]["must_not"].append({
                    "term": {"availability_status": "out_of_stock"}
                })
            
            response = await self.es_manager.search(
                self.index_name,
                search_query,
                size=limit,
                from_=0,
                sort=[{"_score": {"order": "desc"}}]
            )
            
            similar_products = []
            for hit in response.get("hits", {}).get("hits", []):
                product = hit["_source"]
                product["_score"] = hit.get("_score", 0)
                product["similarity_reason"] = self._get_similarity_reason(
                    source_product, product
                )
                similar_products.append(product)
            
            return similar_products
        
        except Exception as e:
            logger.error(f"Error getting similar products: {e}")
            return []
    
    async def get_alternative_products(
        self,
        out_of_stock_product_id: str,
        user_location: Optional[Dict[str, str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get alternative products when the desired product is out of stock."""
        try:
            # Get the out-of-stock product details
            source_product = await self.es_manager.get_document(
                self.index_name, out_of_stock_product_id
            )
            
            if not source_product:
                return []
            
            # Build query for alternatives with enhanced criteria
            search_query = {
                "bool": {
                    "must": [
                        {"term": {"is_active": True}},
                        {"terms": {"availability_status": ["available", "limited_stock"]}}
                    ],
                    "should": [
                        # Same category (very important for alternatives)
                        {
                            "term": {
                                "category_id": {
                                    "value": source_product.get("category_id"),
                                    "boost": 8.0
                                }
                            }
                        },
                        # Similar price range (±50% for alternatives)
                        {
                            "range": {
                                "base_price": {
                                    "gte": source_product.get("base_price", 0) * 0.5,
                                    "lte": source_product.get("base_price", 0) * 1.5,
                                    "boost": 4.0
                                }
                            }
                        },
                        # Same or better quality grade
                        {
                            "terms": {
                                "quality_grade": self._get_quality_alternatives(
                                    source_product.get("quality_grade", "standard")
                                ),
                                "boost": 3.0
                            }
                        },
                        # Location preference
                        self._build_location_boost(user_location, 2.0),
                        # Tags similarity
                        {
                            "terms": {
                                "tags": source_product.get("tags", []),
                                "boost": 2.5
                            }
                        },
                        # Search keywords overlap
                        {
                            "terms": {
                                "search_keywords": source_product.get("search_keywords", []),
                                "boost": 2.0
                            }
                        }
                    ],
                    "must_not": [
                        {"term": {"id": out_of_stock_product_id}}
                    ],
                    "minimum_should_match": 1
                }
            }
            
            response = await self.es_manager.search(
                self.index_name,
                search_query,
                size=limit,
                from_=0,
                sort=[{"_score": {"order": "desc"}}]
            )
            
            alternatives = []
            for hit in response.get("hits", {}).get("hits", []):
                product = hit["_source"]
                product["_score"] = hit.get("_score", 0)
                product["alternative_reason"] = self._get_alternative_reason(
                    source_product, product
                )
                alternatives.append(product)
            
            return alternatives
        
        except Exception as e:
            logger.error(f"Error getting alternative products: {e}")
            return []
    
    async def get_trending_products(
        self,
        category: Optional[str] = None,
        location: Optional[Dict[str, str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending products based on recent activity and popularity."""
        try:
            # Build query for trending products
            search_query = {
                "bool": {
                    "must": [
                        {"term": {"is_active": True}},
                        {"terms": {"availability_status": ["available", "limited_stock"]}}
                    ],
                    "should": [
                        # Featured products get higher score
                        {"term": {"is_featured": {"value": True, "boost": 3.0}}},
                        # Recent products (created in last 30 days)
                        {
                            "range": {
                                "created_at": {
                                    "gte": (datetime.now() - timedelta(days=30)).isoformat(),
                                    "boost": 2.0
                                }
                            }
                        },
                        # Recently updated products
                        {
                            "range": {
                                "updated_at": {
                                    "gte": (datetime.now() - timedelta(days=7)).isoformat(),
                                    "boost": 1.5
                                }
                            }
                        }
                    ]
                }
            }
            
            # Add category filter if specified
            if category:
                search_query["bool"]["must"].append({
                    "term": {"category_id": category}
                })
            
            # Add location boost if specified
            if location:
                location_boost = self._build_location_boost(location, 1.5)
                if location_boost:
                    search_query["bool"]["should"].append(location_boost)
            
            response = await self.es_manager.search(
                self.index_name,
                search_query,
                size=limit,
                from_=0,
                sort=[
                    {"_score": {"order": "desc"}},
                    {"updated_at": {"order": "desc"}}
                ]
            )
            
            trending = []
            for hit in response.get("hits", {}).get("hits", []):
                product = hit["_source"]
                product["_score"] = hit.get("_score", 0)
                product["trending_score"] = self._calculate_trending_score(product)
                trending.append(product)
            
            return trending
        
        except Exception as e:
            logger.error(f"Error getting trending products: {e}")
            return []
    
    def _get_similarity_reason(self, source: Dict, similar: Dict) -> str:
        """Generate a human-readable reason for similarity."""
        reasons = []
        
        if source.get("category_id") == similar.get("category_id"):
            reasons.append("same category")
        
        if abs(source.get("base_price", 0) - similar.get("base_price", 0)) < source.get("base_price", 0) * 0.3:
            reasons.append("similar price")
        
        if source.get("quality_grade") == similar.get("quality_grade"):
            reasons.append("same quality")
        
        if source.get("location", {}).get("state") == similar.get("location", {}).get("state"):
            reasons.append("same region")
        
        return ", ".join(reasons) if reasons else "related product"
    
    def _get_alternative_reason(self, source: Dict, alternative: Dict) -> str:
        """Generate a human-readable reason for alternative suggestion."""
        reasons = []
        
        if source.get("category_id") == alternative.get("category_id"):
            reasons.append("same category")
        
        source_price = source.get("base_price", 0)
        alt_price = alternative.get("base_price", 0)
        if alt_price < source_price:
            reasons.append("lower price")
        elif alt_price > source_price:
            reasons.append("premium option")
        else:
            reasons.append("similar price")
        
        if alternative.get("quality_grade") in ["premium", "organic"]:
            reasons.append("higher quality")
        
        return ", ".join(reasons) if reasons else "good alternative"
    
    def _get_quality_alternatives(self, current_quality: str) -> List[str]:
        """Get quality grades that are acceptable alternatives."""
        quality_hierarchy = {
            "economy": ["economy", "standard", "premium", "organic"],
            "standard": ["standard", "premium", "organic"],
            "premium": ["premium", "organic"],
            "organic": ["organic", "premium"],
            "fair_trade": ["fair_trade", "organic", "premium"]
        }
        return quality_hierarchy.get(current_quality, ["standard", "premium"])
    
    def _build_location_boost(self, location: Optional[Dict[str, str]], boost: float) -> Optional[Dict]:
        """Build location-based boost query."""
        if not location:
            return None
        
        location_should = []
        
        if location.get("city"):
            location_should.append({
                "term": {"location.city": {"value": location["city"], "boost": boost}}
            })
        
        if location.get("state"):
            location_should.append({
                "term": {"location.state": {"value": location["state"], "boost": boost * 0.7}}
            })
        
        if location_should:
            return {"bool": {"should": location_should}}
        
        return None
    
    def _calculate_trending_score(self, product: Dict) -> float:
        """Calculate a trending score for a product."""
        score = 0.0
        
        # Base score for being active and available
        if product.get("is_active"):
            score += 1.0
        
        if product.get("availability_status") == "available":
            score += 2.0
        elif product.get("availability_status") == "limited_stock":
            score += 1.5
        
        # Featured products get bonus
        if product.get("is_featured"):
            score += 3.0
        
        # Recent creation bonus
        created_at = product.get("created_at")
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_old = (datetime.now() - created_date.replace(tzinfo=None)).days
                if days_old < 7:
                    score += 2.0
                elif days_old < 30:
                    score += 1.0
            except:
                pass
        
        # Quality bonus
        quality_bonus = {
            "premium": 1.5,
            "organic": 2.0,
            "fair_trade": 1.8,
            "standard": 1.0,
            "economy": 0.8
        }
        score += quality_bonus.get(product.get("quality_grade", "standard"), 1.0)
        
        return score


class ProductSearchService:
    """Service for product search and indexing operations."""
    
    def __init__(self):
        """Initialize the product search service."""
        self.es_manager = get_elasticsearch_manager()
        self.index_name = "products"
        self.recommendation_engine = ProductRecommendationEngine(self.es_manager)
    
    async def initialize_index(self) -> bool:
        """Initialize the products index with proper mapping."""
        mapping = {
            "properties": {
                "id": {"type": "keyword"},
                "vendor_id": {"type": "keyword"},
                "category_id": {"type": "keyword"},
                "sku": {"type": "keyword"},
                
                # Multilingual text fields
                "names": {
                    "type": "object",
                    "properties": {
                        "hi": {"type": "text", "analyzer": "standard"},
                        "en": {"type": "text", "analyzer": "english"},
                        "ta": {"type": "text", "analyzer": "standard"},
                        "te": {"type": "text", "analyzer": "standard"},
                        "bn": {"type": "text", "analyzer": "standard"},
                        "mr": {"type": "text", "analyzer": "standard"},
                        "gu": {"type": "text", "analyzer": "standard"},
                        "kn": {"type": "text", "analyzer": "standard"},
                        "ml": {"type": "text", "analyzer": "standard"},
                        "pa": {"type": "text", "analyzer": "standard"},
                    }
                },
                "descriptions": {
                    "type": "object",
                    "properties": {
                        "hi": {"type": "text", "analyzer": "standard"},
                        "en": {"type": "text", "analyzer": "english"},
                        "ta": {"type": "text", "analyzer": "standard"},
                        "te": {"type": "text", "analyzer": "standard"},
                        "bn": {"type": "text", "analyzer": "standard"},
                        "mr": {"type": "text", "analyzer": "standard"},
                        "gu": {"type": "text", "analyzer": "standard"},
                        "kn": {"type": "text", "analyzer": "standard"},
                        "ml": {"type": "text", "analyzer": "standard"},
                        "pa": {"type": "text", "analyzer": "standard"},
                    }
                },
                
                # Pricing and quantity
                "base_price": {"type": "float"},
                "currency": {"type": "keyword"},
                "unit": {"type": "keyword"},
                "minimum_order_quantity": {"type": "float"},
                "maximum_order_quantity": {"type": "float"},
                
                # Product attributes
                "quality_grade": {"type": "keyword"},
                "condition": {"type": "keyword"},
                "availability_status": {"type": "keyword"},
                "stock_quantity": {"type": "float"},
                "seasonal_pattern": {"type": "keyword"},
                
                # Location (geo-point for distance queries)
                "location": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "keyword"},
                        "state": {"type": "keyword"},
                        "country": {"type": "keyword"},
                        "coordinates": {"type": "geo_point"},
                        "pincode": {"type": "keyword"},
                    }
                },
                
                # Media and attributes
                "images": {"type": "keyword"},
                "videos": {"type": "keyword"},
                "attributes": {"type": "object", "dynamic": True},
                
                # Search optimization
                "search_keywords": {"type": "text", "analyzer": "standard"},
                "tags": {"type": "keyword"},
                
                # Status and metadata
                "is_active": {"type": "boolean"},
                "is_featured": {"type": "boolean"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "sync_version": {"type": "integer"},
            }
        }
        
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "indian_text": {
                        "type": "standard",
                        "stopwords": "_none_"
                    }
                }
            }
        }
        
        try:
            await self.es_manager.create_index(self.index_name, mapping, settings)
            logger.info(f"Successfully initialized {self.index_name} index")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.index_name} index: {e}")
            return False
    
    async def index_product(self, product_doc: Dict[str, Any]) -> bool:
        """Index a single product document."""
        try:
            product_id = product_doc.get("id")
            if not product_id:
                logger.error("Product document missing ID")
                return False
            
            success = await self.es_manager.index_document(
                self.index_name,
                product_id,
                product_doc,
                refresh=False
            )
            
            if success:
                logger.debug(f"Successfully indexed product {product_id}")
            else:
                logger.error(f"Failed to index product {product_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error indexing product: {e}")
            return False
    
    async def bulk_index_products(self, products: List[Dict[str, Any]]) -> bool:
        """Bulk index multiple products."""
        try:
            success = await self.es_manager.bulk_index(
                self.index_name,
                products,
                refresh=True
            )
            
            if success:
                logger.info(f"Successfully bulk indexed {len(products)} products")
            else:
                logger.error(f"Failed to bulk index {len(products)} products")
            
            return success
        except Exception as e:
            logger.error(f"Error bulk indexing products: {e}")
            return False
    
    async def search_products(
        self,
        query: str,
        language: LanguageCode = LanguageCode.ENGLISH,
        filters: Optional[Dict[str, Any]] = None,
        location: Optional[Dict[str, Any]] = None,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        quality_grades: Optional[List[QualityGrade]] = None,
        availability_statuses: Optional[List[AvailabilityStatus]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "relevance",
        include_alternatives: bool = True,
        boost_local: bool = True
    ) -> Dict[str, Any]:
        """
        Search products with comprehensive filtering and sorting.
        
        Args:
            query: Search query text
            language: Language for search
            filters: Additional filters
            location: Location-based filtering
            price_range: Min and max price tuple
            quality_grades: List of quality grades to filter by
            availability_statuses: List of availability statuses
            page: Page number (1-based)
            page_size: Number of results per page
            sort_by: Sort criteria ("relevance", "price_asc", "price_desc", "date_desc", "trending")
            include_alternatives: Include out-of-stock alternatives
            boost_local: Boost products from user's location
        
        Returns:
            Search results with products, total count, metadata, and recommendations
        """
        try:
            # Build the enhanced search query
            search_query = self._build_enhanced_search_query(
                query, language, filters, location, price_range,
                quality_grades, availability_statuses, boost_local
            )
            
            # Build sort criteria
            sort_criteria = self._build_sort_criteria(sort_by, location)
            
            # Calculate pagination
            from_index = (page - 1) * page_size
            
            # Execute search with aggregations for faceted search
            response = await self.es_manager.search(
                self.index_name,
                search_query,
                size=page_size,
                from_=from_index,
                sort=sort_criteria,
                aggs=self._build_aggregations()
            )
            
            # Process results
            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            products = []
            out_of_stock_products = []
            
            for hit in hits.get("hits", []):
                product = hit["_source"]
                product["_score"] = hit.get("_score", 0)
                product["relevance_factors"] = self._explain_relevance(hit, query)
                
                if product.get("availability_status") == "out_of_stock":
                    out_of_stock_products.append(product)
                else:
                    products.append(product)
            
            # Get alternatives for out-of-stock products if requested
            alternatives = []
            if include_alternatives and out_of_stock_products:
                for oos_product in out_of_stock_products[:3]:  # Limit to first 3
                    product_alternatives = await self.recommendation_engine.get_alternative_products(
                        oos_product["id"], location, limit=2
                    )
                    if product_alternatives:
                        alternatives.extend(product_alternatives)
            
            # Get search suggestions if results are limited
            suggestions = []
            if total < 5 and query:
                suggestions = await self.get_search_suggestions(query, language, limit=3)
            
            # Process aggregations for faceted search
            facets = self._process_aggregations(response.get("aggregations", {}))
            
            return {
                "products": products,
                "out_of_stock": out_of_stock_products,
                "alternatives": alternatives,
                "suggestions": suggestions,
                "facets": facets,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": page * page_size < total,
                "has_prev": page > 1,
                "search_metadata": {
                    "query": query,
                    "language": language.value,
                    "filters_applied": len(filters or {}),
                    "location_boost": boost_local,
                    "alternatives_included": include_alternatives
                }
            }
        
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return {
                "products": [],
                "out_of_stock": [],
                "alternatives": [],
                "suggestions": [],
                "facets": {},
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
                "error": str(e)
            }
    
    async def advanced_search(
        self,
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Advanced search with complex filtering and recommendation logic.
        
        Args:
            search_params: Complex search parameters including:
                - query: Search text
                - language: Search language
                - category_filters: List of categories
                - price_filters: Price range and conditions
                - location_filters: Location-based filters
                - quality_filters: Quality requirements
                - availability_filters: Availability requirements
                - vendor_filters: Vendor-specific filters
                - date_filters: Date range filters
                - custom_filters: Custom attribute filters
                - sort_preferences: Multiple sort criteria
                - recommendation_settings: Recommendation preferences
        
        Returns:
            Enhanced search results with recommendations and analytics
        """
        try:
            # Extract parameters
            query = search_params.get("query", "")
            language = LanguageCode(search_params.get("language", "en"))
            
            # Build complex query
            complex_query = {
                "bool": {
                    "must": [],
                    "should": [],
                    "filter": [],
                    "must_not": []
                }
            }
            
            # Add text search
            if query:
                text_query = self._build_advanced_text_query(query, language)
                complex_query["bool"]["must"].append(text_query)
            
            # Add category filters
            category_filters = search_params.get("category_filters", [])
            if category_filters:
                complex_query["bool"]["filter"].append({
                    "terms": {"category_id": category_filters}
                })
            
            # Add price filters with conditions
            price_filters = search_params.get("price_filters", {})
            if price_filters:
                price_query = self._build_price_filter_query(price_filters)
                if price_query:
                    complex_query["bool"]["filter"].append(price_query)
            
            # Add location filters
            location_filters = search_params.get("location_filters", {})
            if location_filters:
                location_query = self._build_location_filter_query(location_filters)
                if location_query:
                    complex_query["bool"]["filter"].extend(location_query)
            
            # Add quality filters
            quality_filters = search_params.get("quality_filters", [])
            if quality_filters:
                complex_query["bool"]["filter"].append({
                    "terms": {"quality_grade": quality_filters}
                })
            
            # Add availability filters
            availability_filters = search_params.get("availability_filters", [])
            if availability_filters:
                complex_query["bool"]["filter"].append({
                    "terms": {"availability_status": availability_filters}
                })
            
            # Add vendor filters
            vendor_filters = search_params.get("vendor_filters", [])
            if vendor_filters:
                complex_query["bool"]["filter"].append({
                    "terms": {"vendor_id": vendor_filters}
                })
            
            # Add date filters
            date_filters = search_params.get("date_filters", {})
            if date_filters:
                date_query = self._build_date_filter_query(date_filters)
                if date_query:
                    complex_query["bool"]["filter"].append(date_query)
            
            # Add custom attribute filters
            custom_filters = search_params.get("custom_filters", {})
            for key, value in custom_filters.items():
                if isinstance(value, list):
                    complex_query["bool"]["filter"].append({
                        "terms": {f"attributes.{key}": value}
                    })
                else:
                    complex_query["bool"]["filter"].append({
                        "term": {f"attributes.{key}": value}
                    })
            
            # Always filter for active products
            complex_query["bool"]["filter"].append({"term": {"is_active": True}})
            
            # Build sort criteria
            sort_preferences = search_params.get("sort_preferences", ["relevance"])
            sort_criteria = self._build_multi_sort_criteria(sort_preferences, location_filters)
            
            # Execute search
            page = search_params.get("page", 1)
            page_size = search_params.get("page_size", 20)
            from_index = (page - 1) * page_size
            
            response = await self.es_manager.search(
                self.index_name,
                complex_query,
                size=page_size,
                from_=from_index,
                sort=sort_criteria,
                aggs=self._build_advanced_aggregations()
            )
            
            # Process results
            results = self._process_advanced_search_results(response, search_params)
            
            # Add recommendations if requested
            recommendation_settings = search_params.get("recommendation_settings", {})
            if recommendation_settings.get("include_similar", False):
                results["similar_products"] = await self._get_similar_to_results(
                    results["products"][:3], recommendation_settings.get("similar_limit", 5)
                )
            
            if recommendation_settings.get("include_trending", False):
                results["trending_products"] = await self.recommendation_engine.get_trending_products(
                    category=category_filters[0] if category_filters else None,
                    location=location_filters,
                    limit=recommendation_settings.get("trending_limit", 5)
                )
            
            return results
        
        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            return {"error": str(e), "products": [], "total": 0}
    
    def _build_enhanced_search_query(
        self,
        query: str,
        language: LanguageCode,
        filters: Optional[Dict[str, Any]],
        location: Optional[Dict[str, Any]],
        price_range: Optional[Tuple[Decimal, Decimal]],
        quality_grades: Optional[List[QualityGrade]],
        availability_statuses: Optional[List[AvailabilityStatus]],
        boost_local: bool = True
    ) -> Dict[str, Any]:
        """Build enhanced Elasticsearch query with better relevance scoring."""
        
        # Base query structure
        es_query = {
            "bool": {
                "must": [],
                "filter": [],
                "should": [],
                "minimum_should_match": 0
            }
        }
        
        # Add text search with enhanced multilingual support
        if query and query.strip():
            text_query = {
                "bool": {
                    "should": [
                        # Exact phrase match (highest boost)
                        {
                            "multi_match": {
                                "query": query.strip(),
                                "fields": [
                                    f"names.{language.value}^5",
                                    f"descriptions.{language.value}^3",
                                    "search_keywords^4"
                                ],
                                "type": "phrase",
                                "boost": 3.0
                            }
                        },
                        # Best fields match
                        {
                            "multi_match": {
                                "query": query.strip(),
                                "fields": [
                                    f"names.{language.value}^4",
                                    f"descriptions.{language.value}^2.5",
                                    "search_keywords^3",
                                    "tags^2",
                                    # Fallback to English
                                    "names.en^2",
                                    "descriptions.en^1.5"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                                "operator": "or",
                                "boost": 2.0
                            }
                        },
                        # Cross fields match for partial matches
                        {
                            "multi_match": {
                                "query": query.strip(),
                                "fields": [
                                    f"names.{language.value}",
                                    f"descriptions.{language.value}",
                                    "search_keywords",
                                    "tags"
                                ],
                                "type": "cross_fields",
                                "operator": "and",
                                "boost": 1.5
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
            es_query["bool"]["must"].append(text_query)
        else:
            # If no query, match all active products
            es_query["bool"]["must"].append({"match_all": {}})
        
        # Filter by active products only
        es_query["bool"]["filter"].append({"term": {"is_active": True}})
        
        # Price range filter
        if price_range:
            min_price, max_price = price_range
            price_filter = {"range": {"base_price": {}}}
            if min_price is not None:
                price_filter["range"]["base_price"]["gte"] = float(min_price)
            if max_price is not None:
                price_filter["range"]["base_price"]["lte"] = float(max_price)
            es_query["bool"]["filter"].append(price_filter)
        
        # Quality grade filter
        if quality_grades:
            grade_values = [grade.value for grade in quality_grades]
            es_query["bool"]["filter"].append({
                "terms": {"quality_grade": grade_values}
            })
        
        # Availability status filter
        if availability_statuses:
            status_values = [status.value for status in availability_statuses]
            es_query["bool"]["filter"].append({
                "terms": {"availability_status": status_values}
            })
        
        # Location-based filtering and boosting
        if location:
            location_filters = []
            location_boosts = []
            
            if location.get("city"):
                location_filters.append({
                    "term": {"location.city": location["city"]}
                })
                if boost_local:
                    location_boosts.append({
                        "term": {"location.city": {"value": location["city"], "boost": 2.0}}
                    })
            
            if location.get("state"):
                location_filters.append({
                    "term": {"location.state": location["state"]}
                })
                if boost_local:
                    location_boosts.append({
                        "term": {"location.state": {"value": location["state"], "boost": 1.5}}
                    })
            
            if location.get("pincode"):
                location_filters.append({
                    "term": {"location.pincode": location["pincode"]}
                })
                if boost_local:
                    location_boosts.append({
                        "term": {"location.pincode": {"value": location["pincode"], "boost": 2.5}}
                    })
            
            # Geo-distance filter if coordinates provided
            if location.get("coordinates") and location.get("radius_km"):
                location_filters.append({
                    "geo_distance": {
                        "distance": f"{location['radius_km']}km",
                        "location.coordinates": location["coordinates"]
                    }
                })
                if boost_local:
                    location_boosts.append({
                        "geo_distance": {
                            "distance": f"{location['radius_km']}km",
                            "location.coordinates": location["coordinates"],
                            "boost": 3.0
                        }
                    })
            
            # Apply location filters
            if location_filters:
                es_query["bool"]["filter"].extend(location_filters)
            
            # Apply location boosts
            if location_boosts:
                es_query["bool"]["should"].extend(location_boosts)
        
        # Additional custom filters
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    es_query["bool"]["filter"].append({
                        "terms": {key: value}
                    })
                else:
                    es_query["bool"]["filter"].append({
                        "term": {key: value}
                    })
        
        # Boost featured products
        es_query["bool"]["should"].append({
            "term": {"is_featured": {"value": True, "boost": 2.0}}
        })
        
        # Boost products with higher quality grades
        quality_boosts = {
            "premium": 1.8,
            "organic": 2.0,
            "fair_trade": 1.9,
            "standard": 1.0,
            "economy": 0.9
        }
        for quality, boost in quality_boosts.items():
            es_query["bool"]["should"].append({
                "term": {"quality_grade": {"value": quality, "boost": boost}}
            })
        
        # Boost products with good availability
        availability_boosts = {
            "available": 2.0,
            "limited_stock": 1.5,
            "seasonal": 1.2,
            "pre_order": 1.0,
            "out_of_stock": 0.1
        }
        for status, boost in availability_boosts.items():
            es_query["bool"]["should"].append({
                "term": {"availability_status": {"value": status, "boost": boost}}
            })
        
        # Boost recently updated products
        es_query["bool"]["should"].append({
            "range": {
                "updated_at": {
                    "gte": (datetime.now() - timedelta(days=30)).isoformat(),
                    "boost": 1.3
                }
            }
        })
        
        return es_query
    
    def _build_advanced_text_query(self, query: str, language: LanguageCode) -> Dict[str, Any]:
        """Build advanced text query with sophisticated matching."""
        return {
            "bool": {
                "should": [
                    # Exact match (highest priority)
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [f"names.{language.value}^10", "search_keywords^8"],
                            "type": "phrase",
                            "boost": 5.0
                        }
                    },
                    # Prefix match for autocomplete-like behavior
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [f"names.{language.value}^6", "search_keywords^4"],
                            "type": "phrase_prefix",
                            "boost": 3.0
                        }
                    },
                    # Fuzzy match for typos
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                f"names.{language.value}^4",
                                f"descriptions.{language.value}^2",
                                "search_keywords^3"
                            ],
                            "fuzziness": "AUTO",
                            "boost": 2.0
                        }
                    },
                    # Wildcard match for partial words
                    {
                        "query_string": {
                            "query": f"*{query}*",
                            "fields": [f"names.{language.value}^2", "search_keywords^2"],
                            "boost": 1.0
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    
    def _build_price_filter_query(self, price_filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build complex price filter query."""
        price_conditions = []
        
        # Basic range
        if "min_price" in price_filters or "max_price" in price_filters:
            range_filter = {"range": {"base_price": {}}}
            if "min_price" in price_filters:
                range_filter["range"]["base_price"]["gte"] = price_filters["min_price"]
            if "max_price" in price_filters:
                range_filter["range"]["base_price"]["lte"] = price_filters["max_price"]
            price_conditions.append(range_filter)
        
        # Price brackets
        if "price_brackets" in price_filters:
            bracket_conditions = []
            for bracket in price_filters["price_brackets"]:
                bracket_conditions.append({
                    "range": {
                        "base_price": {
                            "gte": bracket.get("min", 0),
                            "lte": bracket.get("max", 999999)
                        }
                    }
                })
            if bracket_conditions:
                price_conditions.append({"bool": {"should": bracket_conditions}})
        
        if price_conditions:
            return {"bool": {"must": price_conditions}}
        
        return None
    
    def _build_location_filter_query(self, location_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build complex location filter query."""
        location_conditions = []
        
        # City filter
        if "cities" in location_filters:
            location_conditions.append({
                "terms": {"location.city": location_filters["cities"]}
            })
        
        # State filter
        if "states" in location_filters:
            location_conditions.append({
                "terms": {"location.state": location_filters["states"]}
            })
        
        # Pincode filter
        if "pincodes" in location_filters:
            location_conditions.append({
                "terms": {"location.pincode": location_filters["pincodes"]}
            })
        
        # Radius filter
        if "center" in location_filters and "radius_km" in location_filters:
            location_conditions.append({
                "geo_distance": {
                    "distance": f"{location_filters['radius_km']}km",
                    "location.coordinates": location_filters["center"]
                }
            })
        
        return location_conditions
    
    def _build_date_filter_query(self, date_filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build date range filter query."""
        date_conditions = []
        
        # Created date range
        if "created_after" in date_filters or "created_before" in date_filters:
            range_filter = {"range": {"created_at": {}}}
            if "created_after" in date_filters:
                range_filter["range"]["created_at"]["gte"] = date_filters["created_after"]
            if "created_before" in date_filters:
                range_filter["range"]["created_at"]["lte"] = date_filters["created_before"]
            date_conditions.append(range_filter)
        
        # Updated date range
        if "updated_after" in date_filters or "updated_before" in date_filters:
            range_filter = {"range": {"updated_at": {}}}
            if "updated_after" in date_filters:
                range_filter["range"]["updated_at"]["gte"] = date_filters["updated_after"]
            if "updated_before" in date_filters:
                range_filter["range"]["updated_at"]["lte"] = date_filters["updated_before"]
            date_conditions.append(range_filter)
        
        if date_conditions:
            return {"bool": {"must": date_conditions}}
        
        return None
    
    def _build_multi_sort_criteria(
        self,
        sort_preferences: List[str],
        location: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Build multiple sort criteria."""
        sort_criteria = []
        
        for sort_pref in sort_preferences:
            if sort_pref == "price_asc":
                sort_criteria.append({"base_price": {"order": "asc"}})
            elif sort_pref == "price_desc":
                sort_criteria.append({"base_price": {"order": "desc"}})
            elif sort_pref == "date_desc":
                sort_criteria.append({"created_at": {"order": "desc"}})
            elif sort_pref == "date_asc":
                sort_criteria.append({"created_at": {"order": "asc"}})
            elif sort_pref == "updated_desc":
                sort_criteria.append({"updated_at": {"order": "desc"}})
            elif sort_pref == "distance" and location and location.get("coordinates"):
                sort_criteria.append({
                    "_geo_distance": {
                        "location.coordinates": location["coordinates"],
                        "order": "asc",
                        "unit": "km"
                    }
                })
            elif sort_pref == "trending":
                # Sort by a combination of factors for trending
                sort_criteria.extend([
                    {"is_featured": {"order": "desc"}},
                    {"updated_at": {"order": "desc"}},
                    {"_score": {"order": "desc"}}
                ])
            elif sort_pref == "relevance":
                sort_criteria.append({"_score": {"order": "desc"}})
        
        # Always add relevance as final sort
        if not any("_score" in str(criteria) for criteria in sort_criteria):
            sort_criteria.append({"_score": {"order": "desc"}})
        
        # Final fallback sort by creation date
        sort_criteria.append({"created_at": {"order": "desc"}})
        
        return sort_criteria
    
    def _build_aggregations(self) -> Dict[str, Any]:
        """Build aggregations for faceted search."""
        return {
            "categories": {
                "terms": {"field": "category_id", "size": 20}
            },
            "quality_grades": {
                "terms": {"field": "quality_grade", "size": 10}
            },
            "availability_status": {
                "terms": {"field": "availability_status", "size": 10}
            },
            "price_ranges": {
                "range": {
                    "field": "base_price",
                    "ranges": [
                        {"to": 100},
                        {"from": 100, "to": 500},
                        {"from": 500, "to": 1000},
                        {"from": 1000, "to": 5000},
                        {"from": 5000}
                    ]
                }
            },
            "locations": {
                "terms": {"field": "location.state", "size": 15}
            }
        }
    
    def _build_advanced_aggregations(self) -> Dict[str, Any]:
        """Build advanced aggregations for detailed analytics."""
        return {
            **self._build_aggregations(),
            "vendors": {
                "terms": {"field": "vendor_id", "size": 20}
            },
            "seasonal_patterns": {
                "terms": {"field": "seasonal_pattern", "size": 10}
            },
            "price_stats": {
                "stats": {"field": "base_price"}
            },
            "recent_products": {
                "date_range": {
                    "field": "created_at",
                    "ranges": [
                        {"from": "now-7d", "key": "last_week"},
                        {"from": "now-30d", "key": "last_month"},
                        {"from": "now-90d", "key": "last_quarter"}
                    ]
                }
            }
        }
    
    def _process_aggregations(self, aggregations: Dict[str, Any]) -> Dict[str, Any]:
        """Process aggregation results into facets."""
        facets = {}
        
        for agg_name, agg_data in aggregations.items():
            if "buckets" in agg_data:
                facets[agg_name] = [
                    {"key": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in agg_data["buckets"]
                ]
            elif agg_name == "price_stats":
                facets[agg_name] = {
                    "min": agg_data.get("min"),
                    "max": agg_data.get("max"),
                    "avg": agg_data.get("avg")
                }
        
        return facets
    
    def _explain_relevance(self, hit: Dict[str, Any], query: str) -> List[str]:
        """Explain why a product is relevant to the search."""
        factors = []
        score = hit.get("_score", 0)
        product = hit["_source"]
        
        if score > 5:
            factors.append("High relevance match")
        elif score > 2:
            factors.append("Good relevance match")
        else:
            factors.append("Basic match")
        
        if product.get("is_featured"):
            factors.append("Featured product")
        
        if product.get("quality_grade") in ["premium", "organic"]:
            factors.append("High quality")
        
        if product.get("availability_status") == "available":
            factors.append("In stock")
        
        return factors
    
    def _process_advanced_search_results(
        self,
        response: Dict[str, Any],
        search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process advanced search results."""
        hits = response.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        products = []
        
        for hit in hits.get("hits", []):
            product = hit["_source"]
            product["_score"] = hit.get("_score", 0)
            product["relevance_factors"] = self._explain_relevance(hit, search_params.get("query", ""))
            products.append(product)
        
        return {
            "products": products,
            "total": total,
            "facets": self._process_aggregations(response.get("aggregations", {})),
            "page": search_params.get("page", 1),
            "page_size": search_params.get("page_size", 20),
            "search_metadata": {
                "complex_query": True,
                "filters_applied": len([k for k in search_params.keys() if k.endswith("_filters")]),
                "sort_criteria": len(search_params.get("sort_preferences", [])),
            }
        }
    
    async def _get_similar_to_results(
        self,
        products: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get products similar to the search results."""
        similar_products = []
        
        for product in products:
            similar = await self.recommendation_engine.get_similar_products(
                product["id"], limit=2
            )
            similar_products.extend(similar)
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_similar = []
        for product in similar_products:
            if product["id"] not in seen_ids:
                seen_ids.add(product["id"])
                unique_similar.append(product)
                if len(unique_similar) >= limit:
                    break
        
        return unique_similar
    
    async def get_search_suggestions(
        self,
        query: str,
        language: LanguageCode = LanguageCode.ENGLISH,
        limit: int = 5
    ) -> List[str]:
        """Get search suggestions based on partial query."""
        try:
            # Use completion suggester or simple prefix query
            search_query = {
                "bool": {
                    "should": [
                        {
                            "prefix": {
                                f"names.{language.value}": {
                                    "value": query.lower(),
                                    "boost": 3.0
                                }
                            }
                        },
                        {
                            "prefix": {
                                "search_keywords": {
                                    "value": query.lower(),
                                    "boost": 2.0
                                }
                            }
                        },
                        {
                            "wildcard": {
                                f"names.{language.value}": {
                                    "value": f"*{query.lower()}*",
                                    "boost": 1.0
                                }
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"is_active": True}}
                    ],
                    "minimum_should_match": 1
                }
            }
            
            response = await self.es_manager.search(
                self.index_name,
                search_query,
                size=limit * 2,  # Get more to filter duplicates
                from_=0
            )
            
            suggestions = []
            seen_suggestions = set()
            
            for hit in response.get("hits", {}).get("hits", []):
                product = hit["_source"]
                name = product.get("names", {}).get(language.value)
                if name and name.lower() not in seen_suggestions:
                    suggestions.append(name)
                    seen_suggestions.add(name.lower())
                    if len(suggestions) >= limit:
                        break
                
                # Also check search keywords
                for keyword in product.get("search_keywords", []):
                    if (keyword.lower().startswith(query.lower()) and 
                        keyword.lower() not in seen_suggestions and 
                        len(suggestions) < limit):
                        suggestions.append(keyword)
                        seen_suggestions.add(keyword.lower())
            
            return suggestions[:limit]
        
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    def _build_sort_criteria(
        self,
        sort_by: str,
        location: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Build sort criteria for search results."""
        
        sort_criteria = []
        
        if sort_by == "price_asc":
            sort_criteria.append({"base_price": {"order": "asc"}})
        elif sort_by == "price_desc":
            sort_criteria.append({"base_price": {"order": "desc"}})
        elif sort_by == "date_desc":
            sort_criteria.append({"created_at": {"order": "desc"}})
        elif sort_by == "date_asc":
            sort_criteria.append({"created_at": {"order": "asc"}})
        elif sort_by == "updated_desc":
            sort_criteria.append({"updated_at": {"order": "desc"}})
        elif sort_by == "trending":
            # Multi-factor trending sort
            sort_criteria.extend([
                {"is_featured": {"order": "desc"}},
                {"updated_at": {"order": "desc"}},
                {"_score": {"order": "desc"}}
            ])
        elif sort_by == "distance" and location and location.get("coordinates"):
            sort_criteria.append({
                "_geo_distance": {
                    "location.coordinates": location["coordinates"],
                    "order": "asc",
                    "unit": "km"
                }
            })
        elif sort_by == "quality_desc":
            # Sort by quality grade (premium first)
            sort_criteria.append({
                "_script": {
                    "type": "number",
                    "script": {
                        "source": """
                            def quality_scores = ['economy': 1, 'standard': 2, 'premium': 3, 'organic': 4, 'fair_trade': 3.5];
                            return quality_scores.getOrDefault(doc['quality_grade'].value, 2);
                        """
                    },
                    "order": "desc"
                }
            })
        
        # Always add relevance score as secondary sort
        if sort_by != "relevance":
            sort_criteria.append({"_score": {"order": "desc"}})
        
        # Final fallback sort by creation date
        sort_criteria.append({"created_at": {"order": "desc"}})
        
        return sort_criteria
    
    async def get_product_suggestions(
        self,
        query: str,
        language: LanguageCode = LanguageCode.ENGLISH,
        limit: int = 5
    ) -> List[str]:
        """Get product name suggestions for autocomplete."""
        return await self.get_search_suggestions(query, language, limit)
    
    async def get_similar_products(
        self,
        product_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get products similar to the given product."""
        return await self.recommendation_engine.get_similar_products(product_id, limit)
    
    async def get_trending_products(
        self,
        category: Optional[str] = None,
        location: Optional[Dict[str, str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending products."""
        return await self.recommendation_engine.get_trending_products(category, location, limit)
    
    async def get_recommendations_for_user(
        self,
        user_id: str,
        user_location: Optional[Dict[str, str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get personalized recommendations for a user."""
        try:
            recommendations = {}
            
            # Get trending products in user's area
            recommendations["trending"] = await self.recommendation_engine.get_trending_products(
                location=user_location, limit=limit//2
            )
            
            # Get recommendations based on user preferences
            if user_preferences:
                preferred_categories = user_preferences.get("categories", [])
                if preferred_categories:
                    category_recommendations = []
                    for category in preferred_categories[:2]:  # Limit to 2 categories
                        category_products = await self.search_products(
                            query="",
                            filters={"category_id": category},
                            location=user_location,
                            sort_by="trending",
                            page_size=3
                        )
                        category_recommendations.extend(category_products.get("products", []))
                    
                    recommendations["based_on_preferences"] = category_recommendations[:limit//2]
            
            # Get recently added products
            recent_products = await self.search_products(
                query="",
                location=user_location,
                sort_by="date_desc",
                page_size=limit//3
            )
            recommendations["recently_added"] = recent_products.get("products", [])
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Error getting user recommendations: {e}")
            return {"trending": [], "based_on_preferences": [], "recently_added": []}
    
    async def search_with_autocorrect(
        self,
        query: str,
        language: LanguageCode = LanguageCode.ENGLISH,
        **kwargs
    ) -> Dict[str, Any]:
        """Search with automatic query correction for typos."""
        try:
            # First try the original query
            results = await self.search_products(query, language, **kwargs)
            
            # If we get very few results, try with fuzzy matching
            if results.get("total", 0) < 3:
                # Build a more fuzzy query
                fuzzy_query = {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        f"names.{language.value}^3",
                                        f"descriptions.{language.value}^2",
                                        "search_keywords^2"
                                    ],
                                    "fuzziness": "2",  # Allow more typos
                                    "prefix_length": 1
                                }
                            },
                            {
                                "wildcard": {
                                    f"names.{language.value}": f"*{query}*"
                                }
                            }
                        ]
                    }
                }
                
                # Execute fuzzy search
                response = await self.es_manager.search(
                    self.index_name,
                    fuzzy_query,
                    size=kwargs.get("page_size", 20)
                )
                
                if response.get("hits", {}).get("total", {}).get("value", 0) > results.get("total", 0):
                    # Process fuzzy results
                    fuzzy_products = []
                    for hit in response.get("hits", {}).get("hits", []):
                        product = hit["_source"]
                        product["_score"] = hit.get("_score", 0)
                        product["autocorrected"] = True
                        fuzzy_products.append(product)
                    
                    results["products"] = fuzzy_products
                    results["total"] = response.get("hits", {}).get("total", {}).get("value", 0)
                    results["autocorrected"] = True
                    results["original_query"] = query
            
            return results
        
        except Exception as e:
            logger.error(f"Error in autocorrect search: {e}")
            return await self.search_products(query, language, **kwargs)
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete a product from the search index."""
        try:
            success = await self.es_manager.delete_document(
                self.index_name, product_id, refresh=True
            )
            
            if success:
                logger.debug(f"Successfully deleted product {product_id} from index")
            else:
                logger.error(f"Failed to delete product {product_id} from index")
            
            return success
        except Exception as e:
            logger.error(f"Error deleting product from index: {e}")
            return False
    
    async def update_product(self, product_id: str, product_doc: Dict[str, Any]) -> bool:
        """Update a product in the search index."""
        try:
            success = await self.es_manager.update_document(
                self.index_name, product_id, product_doc, refresh=False
            )
            
            if success:
                logger.debug(f"Successfully updated product {product_id} in index")
            else:
                logger.error(f"Failed to update product {product_id} in index")
            
            return success
        except Exception as e:
            logger.error(f"Error updating product in index: {e}")
            return False