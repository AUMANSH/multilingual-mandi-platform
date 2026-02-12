"""
Search functionality for the Multilingual Mandi Platform.

This package contains Elasticsearch integration and search services.
"""

from .product_search import ProductSearchService

__all__ = [
    "ProductSearchService",
]