"""
Simple factory functions for creating test data.

These functions provide a straightforward way to create test data
without the complexity of factory_boy.
"""

import random
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4


def create_location() -> Dict[str, str]:
    """Create a simple location."""
    locations = {
        'Delhi': 'New Delhi',
        'Maharashtra': 'Mumbai',
        'Karnataka': 'Bangalore',
        'Tamil Nadu': 'Chennai',
    }
    state = random.choice(list(locations.keys()))
    return {
        'state': state,
        'city': locations[state],
        'pincode': str(random.randint(100001, 999999))
    }


def create_multilingual_text(base_text: str = None) -> Dict[str, str]:
    """Create multilingual text."""
    if base_text is None:
        base_text = f"Test Product {random.randint(1, 1000)}"
    
    return {
        'en': base_text,
        'hi': f"[Hindi] {base_text}",
        'ta': f"[Tamil] {base_text}"
    }


def create_user_data() -> Dict[str, Any]:
    """Create user data."""
    return {
        'phone_number': f"+91{random.randint(6000000000, 9999999999)}",
        'preferred_language': random.choice(['hi', 'en', 'ta', 'te', 'bn']),
        'location': create_location(),
        'tech_literacy_level': random.choice(['low', 'medium', 'high'])
    }


def create_vendor_data() -> Dict[str, Any]:
    """Create vendor data."""
    user_data = create_user_data()
    user_data.update({
        'business_name': f"Test Business {random.randint(1, 100)}",
        'business_type': random.choice(['retail', 'wholesale', 'distributor']),
        'specializations': ['vegetables', 'fruits']
    })
    return user_data


def create_product_data() -> Dict[str, Any]:
    """Create product data."""
    return {
        'name': create_multilingual_text(),
        'category': random.choice(['vegetables', 'fruits', 'grains']),
        'description': create_multilingual_text("Fresh and high quality"),
        'base_price': Decimal(f"{random.randint(100, 10000) / 100:.2f}"),
        'unit': random.choice(['kg', 'liter', 'piece']),
        'quality_grade': random.choice(['premium', 'standard', 'economy']),
        'availability': random.choice(['in_stock', 'out_of_stock', 'limited'])
    }


def create_negotiation_offer() -> Dict[str, Any]:
    """Create negotiation offer data."""
    return {
        'product_id': str(uuid4()),
        'buyer_id': str(uuid4()),
        'vendor_id': str(uuid4()),
        'offered_price': Decimal(f"{random.randint(100, 5000) / 100:.2f}"),
        'quantity': random.randint(1, 100),
        'unit': random.choice(['kg', 'liter', 'piece']),
        'message': f"Test negotiation message {random.randint(1, 100)}",
        'expires_at': datetime.now() + timedelta(days=random.randint(1, 7))
    }


def create_negotiation_scenario() -> Dict[str, Any]:
    """Create a complete negotiation scenario."""
    return {
        'buyer': create_user_data(),
        'vendor': create_vendor_data(),
        'product': create_product_data(),
        'offer': create_negotiation_offer()
    }