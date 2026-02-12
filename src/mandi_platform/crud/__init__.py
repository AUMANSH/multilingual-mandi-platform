"""
CRUD operations for the Multilingual Mandi Platform.

This package contains all database CRUD (Create, Read, Update, Delete) operations.
"""

from .user import UserCRUD, VendorCRUD

__all__ = [
    "UserCRUD",
    "VendorCRUD",
]