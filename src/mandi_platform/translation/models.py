"""
Data models for translation service.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LanguageCode(str, Enum):
    """Supported language codes."""
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


class TranslationEngine(str, Enum):
    """Available translation engines."""
    INLTK = "inltk"
    GOOGLE_TRANSLATE = "google_translate"
    INDIC_NLP = "indic_nlp"


class MarketContext(BaseModel):
    """Market context for contextual translation."""
    product_category: Optional[str] = None
    negotiation_phase: Optional[str] = None
    relationship_type: Optional[str] = None
    regional_context: Optional[str] = None


class TranslationResult(BaseModel):
    """Result of a translation operation."""
    translated_text: str = Field(..., description="The translated text")
    source_language: LanguageCode = Field(..., description="Source language code")
    target_language: LanguageCode = Field(..., description="Target language code")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Translation confidence score"
    )
    engine_used: TranslationEngine = Field(..., description="Translation engine used")
    cached: bool = Field(default=False, description="Whether result was cached")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class LanguageDetectionResult(BaseModel):
    """Result of language detection."""
    detected_language: LanguageCode = Field(..., description="Detected language code")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Detection confidence score"
    )
    all_candidates: Dict[str, float] = Field(
        default_factory=dict, description="All language candidates with scores"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class ContextualTranslationResult(TranslationResult):
    """Result of contextual translation with market-specific adaptations."""
    market_terms_preserved: int = Field(
        default=0, description="Number of market terms preserved"
    )
    cultural_adaptations: int = Field(
        default=0, description="Number of cultural adaptations made"
    )
    context_used: Optional[MarketContext] = Field(
        default=None, description="Market context used for translation"
    )


class TranslationCache(BaseModel):
    """Translation cache entry."""
    source_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    translated_text: str
    context_hash: Optional[str] = None
    confidence_score: float
    engine_used: TranslationEngine
    created_at: float  # Unix timestamp
    usage_count: int = 1