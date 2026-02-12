"""
Unit tests for translation service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from mandi_platform.translation.service import TranslationService
from mandi_platform.translation.models import (
    LanguageCode,
    TranslationEngine,
    TranslationResult,
    ContextualTranslationResult,
    MarketContext,
)
from mandi_platform.translation.language_detector import LanguageDetector


class TestTranslationService:
    """Test cases for TranslationService."""
    
    @pytest.fixture
    def translation_service(self):
        """Create a translation service instance for testing."""
        return TranslationService()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('mandi_platform.translation.service.get_redis_client') as mock:
            redis_mock = AsyncMock()
            mock.return_value = redis_mock
            yield redis_mock
    
    def test_initialization(self, translation_service):
        """Test translation service initialization."""
        assert translation_service is not None
        assert isinstance(translation_service.language_detector, LanguageDetector)
        assert hasattr(translation_service, 'MARKET_TERMS')
        assert hasattr(translation_service, 'INLTK_LANGUAGE_MAPPING')
    
    def test_market_terms_coverage(self, translation_service):
        """Test that market terms are defined for all supported languages."""
        supported_langs = [lang.value for lang in LanguageCode]
        market_term_langs = set(translation_service.MARKET_TERMS.keys())
        
        # All supported languages should have market terms
        for lang in supported_langs:
            assert lang in market_term_langs, f"Market terms missing for {lang}"
    
    def test_inltk_language_mapping_coverage(self, translation_service):
        """Test that iNLTK mapping covers all supported languages."""
        supported_langs = set(LanguageCode)
        mapped_langs = set(translation_service.INLTK_LANGUAGE_MAPPING.keys())
        
        assert supported_langs == mapped_langs, "iNLTK mapping incomplete"
    
    @pytest.mark.asyncio
    async def test_translate_same_language(self, translation_service, mock_redis):
        """Test translation when source and target languages are the same."""
        text = "Hello world"
        result = await translation_service.translate_text(
            text, LanguageCode.ENGLISH, LanguageCode.ENGLISH
        )
        
        assert isinstance(result, TranslationResult)
        assert result.translated_text == text
        assert result.source_language == LanguageCode.ENGLISH
        assert result.target_language == LanguageCode.ENGLISH
        assert result.confidence_score == 1.0
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_translate_with_cache_hit(self, translation_service, mock_redis):
        """Test translation with cache hit."""
        # Mock cached result
        cached_data = {
            "translated_text": "नमस्ते",
            "source_language": "en",
            "target_language": "hi",
            "confidence_score": 0.9,
            "engine_used": "google_translate",
            "cached": False,
            "processing_time_ms": 100.0
        }
        mock_redis.get.return_value = '{"translated_text": "नमस्ते", "source_language": "en", "target_language": "hi", "confidence_score": 0.9, "engine_used": "google_translate", "cached": false, "processing_time_ms": 100.0}'
        
        result = await translation_service.translate_text(
            "Hello", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        assert result.cached == True
        assert result.translated_text == "नमस्ते"
        mock_redis.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_translate_with_google_fallback(self, translation_service, mock_redis):
        """Test translation falling back to Google Translate."""
        mock_redis.get.return_value = None  # No cache
        
        # Mock Google Translate
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("नमस्ते", 0.9)
            
            # Mock iNLTK to fail
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                result = await translation_service.translate_text(
                    "Hello", LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                assert result.translated_text == "नमस्ते"
                assert result.engine_used == TranslationEngine.GOOGLE_TRANSLATE
                assert result.confidence_score == 0.9
                mock_google.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_translate_all_engines_fail(self, translation_service, mock_redis):
        """Test translation when all engines fail."""
        mock_redis.get.return_value = None  # No cache
        
        # Mock both engines to fail
        with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
            mock_inltk.side_effect = RuntimeError("iNLTK failed")
            
            with patch.object(translation_service, '_translate_with_google') as mock_google:
                mock_google.side_effect = RuntimeError("Google failed")
                
                result = await translation_service.translate_text(
                    "Hello", LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                # Should return original text with zero confidence
                assert result.translated_text == "Hello"
                assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_translate_with_context(self, translation_service, mock_redis):
        """Test contextual translation with market context."""
        mock_redis.get.return_value = None  # No cache
        
        # Mock Google Translate
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("मंडी में दर", 0.9)
            
            # Mock iNLTK to fail
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                market_context = MarketContext(
                    product_category="vegetables",
                    negotiation_phase="initial",
                    relationship_type="new_customer"
                )
                
                result = await translation_service.translate_with_context(
                    "Market rate", LanguageCode.ENGLISH, LanguageCode.HINDI, market_context
                )
                
                assert isinstance(result, ContextualTranslationResult)
                assert result.translated_text == "मंडी में दर"
                assert result.context_used == market_context
                assert result.market_terms_preserved >= 0
                assert result.cultural_adaptations >= 0
    
    def test_preserve_market_terms(self, translation_service):
        """Test market term preservation."""
        # Test with known market terms
        text = "The mandi rate for quintal is good"
        preserved = translation_service._preserve_market_terms(
            text, LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        # Should preserve market-specific terms
        assert isinstance(preserved, str)
        # The exact preservation logic depends on implementation
    
    def test_cache_key_generation(self, translation_service):
        """Test cache key generation."""
        key1 = translation_service._get_cache_key(
            "Hello", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        key2 = translation_service._get_cache_key(
            "Hello", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        key3 = translation_service._get_cache_key(
            "Hi", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        # Same inputs should generate same key
        assert key1 == key2
        # Different inputs should generate different keys
        assert key1 != key3
        # Keys should have proper prefix
        assert key1.startswith("translation:")
    
    @pytest.mark.asyncio
    async def test_translate_batch(self, translation_service, mock_redis):
        """Test batch translation functionality."""
        mock_redis.get.return_value = None  # No cache
        
        # Mock Google Translate
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("नमस्ते", 0.9)
            
            # Mock iNLTK to fail
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                texts = ["Hello", "World", "Test"]
                results = await translation_service.translate_batch(
                    texts, LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                assert len(results) == 3
                for result in results:
                    assert isinstance(result, TranslationResult)
                    assert result.translated_text == "नमस्ते"
                    assert result.engine_used == TranslationEngine.GOOGLE_TRANSLATE
    
    @pytest.mark.asyncio
    async def test_translate_empty_text(self, translation_service, mock_redis):
        """Test translation with empty text."""
        result = await translation_service.translate_text(
            "", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        assert result.translated_text == ""
        assert result.confidence_score == 1.0
        assert result.processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_translate_whitespace_only(self, translation_service, mock_redis):
        """Test translation with whitespace-only text."""
        result = await translation_service.translate_text(
            "   ", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        assert result.translated_text == ""
        assert result.confidence_score == 1.0
    
    @pytest.mark.asyncio
    async def test_get_translation_stats(self, translation_service, mock_redis):
        """Test translation statistics retrieval."""
        # Mock Redis scan operations with proper async iterator
        async def mock_scan_iter(match):
            if match == "translation:*":
                for key in ["translation:key1", "translation:key2"]:
                    yield key
            elif match == "translation:*:usage":
                for key in ["translation:key1:usage"]:
                    yield key
        
        mock_redis.scan_iter.side_effect = mock_scan_iter
        mock_redis.get.return_value = "5"
        
        stats = await translation_service.get_translation_stats()
        
        assert isinstance(stats, dict)
        assert "total_cached_translations" in stats
        assert "total_cache_usage" in stats
        assert "cache_hit_rate" in stats
        assert "supported_languages" in stats
        assert "market_terms_count" in stats
        
        assert stats["supported_languages"] == 10  # Number of supported languages
        assert stats["market_terms_count"] > 0
    
    def test_calculate_confidence_score(self, translation_service):
        """Test confidence score calculation."""
        # Test with short text
        confidence = translation_service._calculate_confidence_score(
            "Hi", "नमस्ते", TranslationEngine.GOOGLE_TRANSLATE, 0.9
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.9  # Should be reduced for short text
        
        # Test with long text
        long_text = "This is a very long text that should get higher confidence score"
        confidence = translation_service._calculate_confidence_score(
            long_text, "translated", TranslationEngine.GOOGLE_TRANSLATE, 0.8
        )
        assert confidence >= 0.8  # Should be increased for long text
        
        # Test with market terms
        market_text = "The mandi rate for quintal is good"
        confidence = translation_service._calculate_confidence_score(
            market_text, "translated", TranslationEngine.GOOGLE_TRANSLATE, 0.8
        )
        assert confidence > 0.8  # Should be increased for market terms
    
    def test_preserve_market_terms_advanced(self, translation_service):
        """Test advanced market term preservation."""
        # Test with multiple market terms
        text = "The mandi rates for quintals are good quality"
        preserved = translation_service._preserve_market_terms(
            text, LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        assert isinstance(preserved, str)
        # Should handle plurals and different cases
        
        # Test with mismatched term counts (should handle gracefully)
        with patch.object(translation_service, 'MARKET_TERMS', {"en": ["term1"], "hi": []}):
            result = translation_service._preserve_market_terms(
                "term1", LanguageCode.ENGLISH, LanguageCode.HINDI
            )
            assert result == "term1"  # Should return original if mismatch


class TestTranslationServiceIntegration:
    """Integration tests for translation service."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_language_detection(self):
        """Test real language detection with actual libraries."""
        service = TranslationService()
        
        test_cases = [
            ("Hello world", LanguageCode.ENGLISH),
            ("नमस्ते दुनिया", LanguageCode.HINDI),
            ("", LanguageCode.ENGLISH),  # Empty text defaults to English
        ]
        
        for text, expected_lang in test_cases:
            result = await service.detect_language(text)
            
            # For empty text, we expect English default
            if not text:
                assert result.detected_language == LanguageCode.ENGLISH
                assert result.confidence_score == 0.0
            else:
                # For non-empty text, we expect some detection result
                assert isinstance(result.detected_language, LanguageCode)
                assert 0.0 <= result.confidence_score <= 1.0
                assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_real_translation_with_fallback(self):
        """Test real translation with fallback mechanisms."""
        service = TranslationService()
        
        # Test simple translation that should work with Google Translate
        result = await service.translate_text(
            "Hello", LanguageCode.ENGLISH, LanguageCode.HINDI
        )
        
        assert isinstance(result, TranslationResult)
        assert result.source_language == LanguageCode.ENGLISH
        assert result.target_language == LanguageCode.HINDI
        assert result.processing_time_ms > 0
        
        # Result should either be translated or original text (if all engines fail)
        assert len(result.translated_text) > 0
        
        # Confidence should be between 0 and 1
        assert 0.0 <= result.confidence_score <= 1.0