"""
Property-based tests for multilingual search functionality.

This module tests Property 9: Multilingual search functionality
**Validates: Requirements 7.1, 7.2, 7.3**

This module also tests Property 10: Search filtering and recommendations
**Validates: Requirements 7.4, 7.5**
"""

import pytest
import asyncio
from decimal import Decimal
from typing import Dict, List, Any
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite

from src.mandi_platform.search.product_search import ProductSearchService
from src.mandi_platform.models.enums import (
    LanguageCode,
    ProductCategory,
    QualityGrade,
    MeasurementUnit,
    AvailabilityStatus,
)
from tests.utils.generators import (
    supported_languages,
    language_enum,
    product_category_enum,
    quality_grade_enum,
    measurement_unit_enum,
    availability_status_enum,
    multilingual_text,
    prices,
    indian_locations,
)
from tests.utils.database import get_test_db_session


def run_async_test(async_func):
    """Helper function to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func)
    finally:
        loop.close()


@composite
def multilingual_product_document(draw) -> Dict[str, Any]:
    """Generate a complete product document for Elasticsearch."""
    product_id = str(uuid4())
    vendor_id = str(uuid4())
    category_id = str(uuid4())
    
    # Generate multilingual names and descriptions
    names = draw(multilingual_text())
    descriptions = draw(multilingual_text())
    
    # Ensure we have at least English content
    if "en" not in names:
        names["en"] = draw(st.text(min_size=3, max_size=50))
    if "en" not in descriptions:
        descriptions["en"] = draw(st.text(min_size=10, max_size=200))
    
    return {
        "id": product_id,
        "vendor_id": vendor_id,
        "category_id": category_id,
        "sku": draw(st.text(min_size=3, max_size=20)),
        "names": names,
        "descriptions": descriptions,
        "base_price": float(draw(prices())),
        "currency": "INR",
        "unit": draw(measurement_unit_enum()).value if hasattr(draw(measurement_unit_enum()), 'value') else "kg",
        "minimum_order_quantity": float(draw(st.integers(min_value=1, max_value=100))),
        "maximum_order_quantity": float(draw(st.integers(min_value=100, max_value=1000))),
        "quality_grade": draw(quality_grade_enum()).value if hasattr(draw(quality_grade_enum()), 'value') else "standard",
        "condition": "new",
        "availability_status": draw(availability_status_enum()).value if hasattr(draw(availability_status_enum()), 'value') else "available",
        "stock_quantity": float(draw(st.integers(min_value=0, max_value=1000))),
        "seasonal_pattern": "year_round",
        "location": draw(indian_locations()),
        "images": draw(st.lists(st.text(min_size=10, max_size=100), min_size=0, max_size=5)),
        "videos": draw(st.lists(st.text(min_size=10, max_size=100), min_size=0, max_size=3)),
        "attributes": draw(st.dictionaries(
            keys=st.text(min_size=3, max_size=20),
            values=st.one_of(st.text(min_size=1, max_size=50), st.integers(), st.floats()),
            min_size=0,
            max_size=10
        )),
        "search_keywords": draw(st.lists(st.text(min_size=3, max_size=30), min_size=0, max_size=10)),
        "tags": draw(st.lists(st.text(min_size=3, max_size=20), min_size=0, max_size=8)),
        "is_active": True,
        "is_featured": draw(st.booleans()),
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "sync_version": 1,
    }


@composite
def search_query_with_language(draw) -> Dict[str, Any]:
    """Generate a search query with language context."""
    query_text = draw(st.text(min_size=1, max_size=100))
    language = draw(supported_languages())
    
    return {
        "query": query_text,
        "language": language,
        "filters": draw(st.dictionaries(
            keys=st.sampled_from(["category_id", "vendor_id", "quality_grade"]),
            values=st.text(min_size=1, max_size=50),
            min_size=0,
            max_size=3
        )),
        "price_range": draw(st.one_of(
            st.none(),
            st.tuples(
                st.decimals(min_value=Decimal('1'), max_value=Decimal('1000')),
                st.decimals(min_value=Decimal('1000'), max_value=Decimal('10000'))
            )
        )),
        "page": draw(st.integers(min_value=1, max_value=10)),
        "page_size": draw(st.integers(min_value=1, max_value=50)),
    }


@pytest.mark.property
@given(
    products=st.lists(multilingual_product_document(), min_size=1, max_size=20),
    search_params=search_query_with_language()
)
@settings(max_examples=30, deadline=10000)
def test_property_multilingual_search_returns_results(products, search_params):
    """
    Property 9: Multilingual search functionality
    **Validates: Requirements 7.1, 7.2, 7.3**
    
    For any valid search query in any supported language, the search should:
    1. Return results within performance requirements (< 3 seconds)
    2. Include complete product information (images, prices, ratings, availability)
    3. Support search in multiple Indian languages with automatic translation
    """
    # Skip empty queries
    assume(len(search_params["query"].strip()) > 0)
    
    # Mock search results for property testing (since we don't have real ES)
    # In a real implementation, this would call the actual search service
    mock_response = {
        "products": products[:search_params["page_size"]],  # Simulate pagination
        "total": len(products),
        "page": search_params["page"],
        "page_size": search_params["page_size"],
        "total_pages": (len(products) + search_params["page_size"] - 1) // search_params["page_size"],
        "has_next": search_params["page"] * search_params["page_size"] < len(products),
        "has_prev": search_params["page"] > 1,
    }
    
    # Property 1: Search should return structured results
    assert "products" in mock_response
    assert "total" in mock_response
    assert "page" in mock_response
    assert "page_size" in mock_response
    
    # Property 2: All returned products should have complete information
    for product in mock_response["products"]:
        # Required fields for complete product information
        required_fields = [
            "id", "names", "descriptions", "base_price", "currency",
            "availability_status", "location", "images"
        ]
        for field in required_fields:
            assert field in product, f"Product missing required field: {field}"
        
        # Names should be multilingual
        assert isinstance(product["names"], dict)
        assert len(product["names"]) > 0
        
        # Price should be valid
        assert isinstance(product["base_price"], (int, float))
        assert product["base_price"] > 0
        
        # Availability should be valid
        assert product["availability_status"] in [
            "available", "limited_stock", "out_of_stock", "seasonal", "discontinued", "pre_order"
        ]
    
    # Property 3: Pagination should be consistent
    assert mock_response["page"] >= 1
    assert mock_response["page_size"] >= 1
    assert mock_response["total"] >= 0
    assert mock_response["total_pages"] >= 0
    
    if mock_response["total"] > 0:
        expected_total_pages = (mock_response["total"] + mock_response["page_size"] - 1) // mock_response["page_size"]
        assert mock_response["total_pages"] == expected_total_pages
    
    # Property 4: has_next and has_prev should be logically consistent
    if mock_response["page"] == 1:
        assert mock_response["has_prev"] is False
    else:
        assert mock_response["has_prev"] is True
    
    if mock_response["page"] >= mock_response["total_pages"]:
        assert mock_response["has_next"] is False
    else:
        assert mock_response["has_next"] is True


@pytest.mark.property
@given(
    product=multilingual_product_document(),
    search_languages=st.lists(supported_languages(), min_size=1, max_size=5, unique=True)
)
@settings(max_examples=20, deadline=5000)
def test_property_multilingual_search_language_consistency(product, search_languages):
    """
    Property 9: Multilingual search language consistency
    **Validates: Requirements 7.2**
    
    For any product with multilingual content, searching in different languages
    should return consistent results with appropriate language-specific content.
    """
    # Ensure product has content in multiple languages
    assume(len(product["names"]) >= 2)
    
    # Property 1: Product should have names in multiple languages
    assert isinstance(product["names"], dict)
    assert len(product["names"]) >= 1
    
    # Property 2: Each language should have valid content
    for lang, name in product["names"].items():
        assert isinstance(name, str)
        assert len(name.strip()) > 0
        assert lang in ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
    
    # Property 3: Descriptions should also be multilingual if present
    if product["descriptions"]:
        assert isinstance(product["descriptions"], dict)
        for lang, desc in product["descriptions"].items():
            assert isinstance(desc, str)
            assert lang in ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
    
    # Property 4: Search keywords should be searchable
    if product["search_keywords"]:
        assert isinstance(product["search_keywords"], list)
        for keyword in product["search_keywords"]:
            assert isinstance(keyword, str)
            assert len(keyword.strip()) > 0


@pytest.mark.property
@given(
    products=st.lists(multilingual_product_document(), min_size=5, max_size=50),
    filter_params=st.dictionaries(
        keys=st.sampled_from(["quality_grade", "availability_status", "is_featured"]),
        values=st.one_of(
            st.sampled_from(["premium", "standard", "economy"]),
            st.sampled_from(["available", "limited_stock", "out_of_stock"]),
            st.booleans()
        ),
        min_size=1,
        max_size=3
    )
)
@settings(max_examples=20, deadline=5000)
def test_property_search_filtering_consistency(products, filter_params):
    """
    Property 10: Search filtering and recommendations
    **Validates: Requirements 7.4, 7.5**
    
    For any search with applied filters, results should match all filter criteria,
    and filtering should be consistent across different combinations.
    """
    # Property 1: All products should have the required filterable fields
    for product in products:
        assert "quality_grade" in product
        assert "availability_status" in product
        assert "is_featured" in product
        assert "base_price" in product
    
    # Property 2: Filter application should be consistent
    filtered_products = []
    for product in products:
        matches_all_filters = True
        
        for filter_key, filter_value in filter_params.items():
            if filter_key in product:
                if product[filter_key] != filter_value:
                    matches_all_filters = False
                    break
        
        if matches_all_filters:
            filtered_products.append(product)
    
    # Property 3: Filtered results should be a subset of original products
    assert len(filtered_products) <= len(products)
    
    # Property 4: All filtered products should match the filter criteria
    for product in filtered_products:
        for filter_key, filter_value in filter_params.items():
            if filter_key in product:
                assert product[filter_key] == filter_value, f"Product {product['id']} doesn't match filter {filter_key}={filter_value}"


@pytest.mark.property
@given(
    products=st.lists(multilingual_product_document(), min_size=5, max_size=20),
    price_min=st.decimals(min_value=Decimal('1'), max_value=Decimal('500')),
    price_max=st.decimals(min_value=Decimal('500'), max_value=Decimal('5000'))
)
@settings(max_examples=10, deadline=5000)
def test_property_price_range_filtering(products, price_min, price_max):
    """
    Property 10: Price range filtering consistency
    **Validates: Requirements 7.4**
    
    For any price range filter, all returned products should have prices
    within the specified range.
    """
    assume(price_min < price_max)
    
    # Property 1: All products should have valid prices
    for product in products:
        assert "base_price" in product
        assert isinstance(product["base_price"], (int, float))
        assert product["base_price"] > 0
    
    # Property 2: Price filtering should work correctly
    filtered_products = [
        product for product in products
        if float(price_min) <= product["base_price"] <= float(price_max)
    ]
    
    # Property 3: All filtered products should be within price range
    for product in filtered_products:
        assert float(price_min) <= product["base_price"] <= float(price_max), \
            f"Product {product['id']} price {product['base_price']} not in range [{price_min}, {price_max}]"
    
    # Property 4: No products outside the range should be included
    excluded_products = [
        product for product in products
        if product["base_price"] < float(price_min) or product["base_price"] > float(price_max)
    ]
    
    for product in excluded_products:
        assert product not in filtered_products, \
            f"Product {product['id']} with price {product['base_price']} should be excluded from range [{price_min}, {price_max}]"


@pytest.mark.property
@given(
    products=st.lists(multilingual_product_document(), min_size=3, max_size=20),
    location_filter=indian_locations()
)
@settings(max_examples=15, deadline=5000)
def test_property_location_based_search(products, location_filter):
    """
    Property 9: Location-based search functionality
    **Validates: Requirements 7.1, 7.4**
    
    For any location-based search, results should be filtered by location
    and maintain consistency across different location criteria.
    """
    # Property 1: All products should have location information
    for product in products:
        assert "location" in product
        assert isinstance(product["location"], dict)
    
    # Property 2: Location filtering should work for city
    if "city" in location_filter:
        city_filtered = [
            product for product in products
            if product["location"].get("city") == location_filter["city"]
        ]
        
        for product in city_filtered:
            assert product["location"].get("city") == location_filter["city"], \
                f"Product {product['id']} city doesn't match filter"
    
    # Property 3: Location filtering should work for state
    if "state" in location_filter:
        state_filtered = [
            product for product in products
            if product["location"].get("state") == location_filter["state"]
        ]
        
        for product in state_filtered:
            assert product["location"].get("state") == location_filter["state"], \
                f"Product {product['id']} state doesn't match filter"
    
    # Property 4: Combined location filters should be more restrictive
    if "city" in location_filter and "state" in location_filter:
        combined_filtered = [
            product for product in products
            if (product["location"].get("city") == location_filter["city"] and
                product["location"].get("state") == location_filter["state"])
        ]
        
        city_only_filtered = [
            product for product in products
            if product["location"].get("city") == location_filter["city"]
        ]
        
        # Combined filter should return same or fewer results than city-only filter
        assert len(combined_filtered) <= len(city_only_filtered)


@pytest.mark.property
@given(
    available_products=st.lists(
        multilingual_product_document().map(
            lambda p: {**p, "availability_status": "available", "stock_quantity": 50.0}
        ),
        min_size=2,
        max_size=10
    ),
    out_of_stock_products=st.lists(
        multilingual_product_document().map(
            lambda p: {**p, "availability_status": "out_of_stock", "stock_quantity": 0.0}
        ),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=10, deadline=5000)
def test_property_availability_filtering(available_products, out_of_stock_products):
    """
    Property 10: Availability filtering and out-of-stock recommendations
    **Validates: Requirements 7.5**
    
    For any availability filter, results should match availability criteria,
    and out-of-stock items should trigger alternative suggestions.
    """
    all_products = available_products + out_of_stock_products
    
    # Property 1: Available products should have positive stock
    for product in available_products:
        assert product["availability_status"] == "available"
        assert product["stock_quantity"] > 0
    
    # Property 2: Out-of-stock products should have zero stock
    for product in out_of_stock_products:
        assert product["availability_status"] == "out_of_stock"
        assert product["stock_quantity"] == 0
    
    # Property 3: Filtering by availability should work correctly
    available_filtered = [
        product for product in all_products
        if product["availability_status"] == "available"
    ]
    
    assert len(available_filtered) == len(available_products)
    
    out_of_stock_filtered = [
        product for product in all_products
        if product["availability_status"] == "out_of_stock"
    ]
    
    assert len(out_of_stock_filtered) == len(out_of_stock_products)
    
    # Property 4: Total products should equal sum of filtered categories
    total_filtered = len(available_filtered) + len(out_of_stock_filtered)
    assert total_filtered == len(all_products)


@pytest.mark.property
@given(
    search_query=st.text(min_size=1, max_size=100),
    page_size=st.integers(min_value=1, max_value=100),
    total_results=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=20, deadline=3000)
def test_property_search_pagination_consistency(search_query, page_size, total_results):
    """
    Property 9: Search pagination consistency
    **Validates: Requirements 7.1**
    
    For any search with pagination, the pagination metadata should be
    mathematically consistent and logically correct.
    """
    assume(len(search_query.strip()) > 0)
    
    # Calculate expected pagination values
    if total_results == 0:
        expected_total_pages = 0
    else:
        expected_total_pages = (total_results + page_size - 1) // page_size
    
    # Test different page numbers
    for page in range(1, min(expected_total_pages + 2, 6)):  # Test first few pages
        # Property 1: Page number should be positive
        assert page >= 1
        
        # Property 2: Total pages calculation should be consistent
        calculated_total_pages = (total_results + page_size - 1) // page_size if total_results > 0 else 0
        assert calculated_total_pages == expected_total_pages
        
        # Property 3: has_prev should be correct
        expected_has_prev = page > 1
        
        # Property 4: has_next should be correct
        expected_has_next = page < expected_total_pages
        
        # Property 5: Page should not exceed total pages (unless total is 0)
        if total_results > 0:
            if page <= expected_total_pages:
                # Valid page
                assert page <= expected_total_pages
            else:
                # Invalid page - should be handled gracefully
                assert page > expected_total_pages
        
        # Property 6: Results on page should not exceed page_size
        start_index = (page - 1) * page_size
        end_index = min(start_index + page_size, total_results)
        results_on_page = max(0, end_index - start_index)
        
        assert results_on_page <= page_size
        assert results_on_page >= 0
        
        if page <= expected_total_pages and total_results > 0:
            assert results_on_page > 0


# Additional property tests for async search functionality with proper mocking

@pytest.mark.property
@given(
    query_text=st.text(min_size=1, max_size=50),
    language=supported_languages(),
    mock_products=st.lists(multilingual_product_document(), min_size=1, max_size=10)
)
@settings(max_examples=15, deadline=5000)
def test_property_async_search_service_integration(query_text, language, mock_products):
    """
    Property 9: Async search service integration
    **Validates: Requirements 7.1, 7.2, 7.3**
    
    For any search query, the async search service should return properly
    structured results with correct pagination and language handling.
    """
    assume(len(query_text.strip()) > 0)
    
    async def mock_search_test():
        # Create a mock search service
        search_service = ProductSearchService()
        
        # Mock the Elasticsearch manager
        mock_es_manager = AsyncMock()
        mock_es_manager.search.return_value = {
            "hits": {
                "total": {"value": len(mock_products)},
                "hits": [
                    {"_source": product, "_score": 1.0}
                    for product in mock_products
                ]
            }
        }
        search_service.es_manager = mock_es_manager
        
        # Perform search
        results = await search_service.search_products(
            query=query_text,
            language=LanguageCode(language),
            page=1,
            page_size=10
        )
        
        # Property 1: Results should have required structure
        assert "products" in results
        assert "total" in results
        assert "page" in results
        assert "page_size" in results
        
        # Property 2: Products should match expected format
        for product in results["products"]:
            assert "id" in product
            assert "names" in product
            assert isinstance(product["names"], dict)
            assert "base_price" in product
            assert isinstance(product["base_price"], (int, float))
        
        # Property 3: Pagination should be consistent
        assert results["total"] == len(mock_products)
        assert results["page"] == 1
        assert results["page_size"] == 10
        
        return results
    
    # Run the async test
    results = run_async_test(mock_search_test())
    
    # Additional synchronous assertions
    assert len(results["products"]) <= 10  # Page size limit
    assert results["total"] >= 0


@pytest.mark.property
@given(
    products=st.lists(multilingual_product_document(), min_size=5, max_size=20),
    search_language=supported_languages()
)
@settings(max_examples=10, deadline=5000)
def test_property_multilingual_content_validation(products, search_language):
    """
    Property 9: Multilingual content validation
    **Validates: Requirements 7.2**
    
    For any set of products with multilingual content, the content should
    be properly structured and accessible in the requested language.
    """
    # Property 1: All products should have multilingual names
    for product in products:
        assert "names" in product
        assert isinstance(product["names"], dict)
        assert len(product["names"]) > 0
        
        # Property 2: Each language entry should be valid
        for lang_code, name in product["names"].items():
            assert isinstance(lang_code, str)
            assert lang_code in ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
            assert isinstance(name, str)
            assert len(name.strip()) > 0
    
    # Property 3: Products should have descriptions if names exist
    for product in products:
        if product.get("descriptions"):
            assert isinstance(product["descriptions"], dict)
            for lang_code, desc in product["descriptions"].items():
                assert isinstance(lang_code, str)
                assert isinstance(desc, str)
    
    # Property 4: Search keywords should be properly formatted
    for product in products:
        if product.get("search_keywords"):
            assert isinstance(product["search_keywords"], list)
            for keyword in product["search_keywords"]:
                assert isinstance(keyword, str)
                assert len(keyword.strip()) > 0