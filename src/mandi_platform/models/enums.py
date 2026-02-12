"""
Enums and constants for the Multilingual Mandi Platform.

This module defines all the enumeration types used throughout the application.
"""

import enum


class LanguageCode(str, enum.Enum):
    """Supported Indian languages."""
    HINDI = "hi"
    ENGLISH = "en"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


class TechLiteracyLevel(str, enum.Enum):
    """User's technology literacy level."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class VerificationStatus(str, enum.Enum):
    """User verification status."""
    UNVERIFIED = "unverified"
    PHONE_VERIFIED = "phone_verified"
    DOCUMENT_VERIFIED = "document_verified"
    FULLY_VERIFIED = "fully_verified"


class BusinessType(str, enum.Enum):
    """Types of businesses for vendors."""
    INDIVIDUAL_TRADER = "individual_trader"
    SMALL_BUSINESS = "small_business"
    COOPERATIVE = "cooperative"
    WHOLESALER = "wholesaler"
    RETAILER = "retailer"
    FARMER = "farmer"
    MANUFACTURER = "manufacturer"


class MarketReputation(str, enum.Enum):
    """Market reputation levels for vendors."""
    NEW = "new"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    TRUSTED = "trusted"
    PREMIUM = "premium"


class PaymentMethod(str, enum.Enum):
    """Supported payment methods."""
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"


class ProductCategory(str, enum.Enum):
    """Product categories in the marketplace."""
    GRAINS = "grains"
    VEGETABLES = "vegetables"
    FRUITS = "fruits"
    SPICES = "spices"
    DAIRY = "dairy"
    MEAT = "meat"
    SEAFOOD = "seafood"
    PULSES = "pulses"
    OILS = "oils"
    TEXTILES = "textiles"
    HANDICRAFTS = "handicrafts"
    ELECTRONICS = "electronics"
    TOOLS = "tools"
    HOUSEHOLD = "household"
    OTHER = "other"


class QualityGrade(str, enum.Enum):
    """Quality grades for products."""
    PREMIUM = "premium"
    STANDARD = "standard"
    ECONOMY = "economy"
    ORGANIC = "organic"
    FAIR_TRADE = "fair_trade"


class MeasurementUnit(str, enum.Enum):
    """Measurement units for products."""
    # Weight units
    KILOGRAM = "kg"
    GRAM = "g"
    QUINTAL = "quintal"
    TON = "ton"
    
    # Volume units
    LITER = "liter"
    MILLILITER = "ml"
    
    # Count units
    PIECE = "piece"
    DOZEN = "dozen"
    BUNDLE = "bundle"
    BAG = "bag"
    BOX = "box"
    
    # Traditional Indian units
    MAUND = "maund"  # ~37.3 kg
    SER = "ser"      # ~0.933 kg
    TOLA = "tola"    # ~11.7 g
    BIGHA = "bigha"  # Area unit, varies by region
    ACRE = "acre"


class AvailabilityStatus(str, enum.Enum):
    """Product availability status."""
    AVAILABLE = "available"
    LIMITED_STOCK = "limited_stock"
    OUT_OF_STOCK = "out_of_stock"
    SEASONAL = "seasonal"
    DISCONTINUED = "discontinued"
    PRE_ORDER = "pre_order"


class SeasonalPattern(str, enum.Enum):
    """Seasonal availability patterns."""
    YEAR_ROUND = "year_round"
    SUMMER = "summer"
    MONSOON = "monsoon"
    WINTER = "winter"
    SPRING = "spring"
    HARVEST_SEASON = "harvest_season"
    FESTIVAL_SEASON = "festival_season"


class ProductCondition(str, enum.Enum):
    """Product condition."""
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    REFURBISHED = "refurbished"


class PriceSource(str, enum.Enum):
    """Sources of price data."""
    VENDOR_LISTED = "vendor_listed"
    MARKET_API = "market_api"
    GOVERNMENT_DATA = "government_data"
    HISTORICAL_AVERAGE = "historical_average"
    ML_PREDICTION = "ml_prediction"


class MarketConditions(str, enum.Enum):
    """Market condition indicators."""
    NORMAL = "normal"
    HIGH_DEMAND = "high_demand"
    LOW_DEMAND = "low_demand"
    SUPPLY_SHORTAGE = "supply_shortage"
    OVERSUPPLY = "oversupply"
    SEASONAL_PEAK = "seasonal_peak"
    FESTIVAL_RUSH = "festival_rush"