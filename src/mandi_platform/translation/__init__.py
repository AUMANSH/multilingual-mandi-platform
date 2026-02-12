"""
Translation service for multilingual support.

This module provides translation capabilities for Indian languages using
multiple NLP libraries and fallback mechanisms.
"""

from .service import TranslationService
from .language_detector import LanguageDetector
from .models import (
    TranslationResult,
    LanguageDetectionResult,
    ContextualTranslationResult,
    MarketContext,
)

__all__ = [
    "TranslationService",
    "LanguageDetector", 
    "TranslationResult",
    "LanguageDetectionResult",
    "ContextualTranslationResult",
    "MarketContext",
]