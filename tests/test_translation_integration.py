"""
Integration tests for the complete translation service.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from mandi_platform.translation.service import TranslationService
from mandi_platform.translation.models import (
    LanguageCode,
    TranslationEngine,
    MarketContext,
)


class TestTranslationServiceIntegration:
    """Integration tests for the complete translation service."""
    
    @pytest.fixture
    def translation_service(self):
        """Create a translation service instance for testing."""
        return TranslationService()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for integration tests."""
        with patch('mandi_platform.translation.service.get_redis_client') as mock:
            redis_mock = AsyncMock()
            mock.return_value = redis_mock
            yield redis_mock
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_translation_workflow(self, translation_service, mock_redis):
        """Test the complete translation workflow with caching."""
        # Setup cache behavior
        mock_redis.get.side_effect = [None, '{"translated_text": "नमस्ते दुनिया", "source_language": "en", "target_language": "hi", "confidence_score": 0.9, "engine_used": "google_translate", "cached": false, "processing_time_ms": 100.0}']
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        # Mock Google Translate to avoid external API calls
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("नमस्ते दुनिया", 0.9)
            
            # Mock iNLTK to fail and fallback to Google
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                # First translation - should hit Google Translate
                result1 = await translation_service.translate_text(
                    "Hello world", LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                assert result1.translated_text == "नमस्ते दुनिया"
                assert result1.engine_used == TranslationEngine.GOOGLE_TRANSLATE
                assert result1.confidence_score > 0.8
                assert not result1.cached
                
                # Second translation - should hit cache
                result2 = await translation_service.translate_text(
                    "Hello world", LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                assert result2.translated_text == "नमस्ते दुनिया"
                assert result2.cached
                
                # Verify Google Translate was only called once
                assert mock_google.call_count == 1
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_contextual_translation_with_market_terms(self, translation_service, mock_redis):
        """Test contextual translation with market terminology preservation."""
        # Setup cache behavior
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        # Mock Google Translate
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("मंडी दर अच्छा है", 0.9)
            
            # Mock iNLTK to fail
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                market_context = MarketContext(
                    product_category="vegetables",
                    negotiation_phase="initial",
                    relationship_type="new_customer"
                )
                
                result = await translation_service.translate_with_context(
                    "Mandi rate is good", 
                    LanguageCode.ENGLISH, 
                    LanguageCode.HINDI,
                    market_context
                )
                
                assert result.translated_text == "मंडी दर अच्छा है"
                assert result.context_used == market_context
                assert result.market_terms_preserved >= 0
                assert result.cultural_adaptations >= 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_translation_performance(self, translation_service, mock_redis):
        """Test batch translation performance and consistency."""
        # Setup cache behavior
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        # Mock Google Translate
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("अनुवादित", 0.9)
            
            # Mock iNLTK to fail
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                texts = [
                    "Hello",
                    "World", 
                    "Test translation",
                    "Market rate",
                    "Quality grade"
                ]
                
                results = await translation_service.translate_batch(
                    texts, LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                assert len(results) == len(texts)
                
                for result in results:
                    assert result.translated_text == "अनुवादित"
                    assert result.engine_used == TranslationEngine.GOOGLE_TRANSLATE
                    assert result.confidence_score > 0.8
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_translation_stats_collection(self, translation_service, mock_redis):
        """Test translation statistics collection."""
        # Setup cache and stats behavior
        async def mock_scan_iter(match):
            if match == "translation:*":
                for key in ["translation:key1", "translation:key2"]:
                    yield key
            elif match == "translation:*:usage":
                for key in ["translation:key1:usage"]:
                    yield key
        
        mock_redis.scan_iter.side_effect = mock_scan_iter
        mock_redis.get.return_value = "5"
        mock_redis.setex.return_value = True
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        # Mock Google Translate
        with patch.object(translation_service, '_translate_with_google') as mock_google:
            mock_google.return_value = ("परीक्षण", 0.9)
            
            # Mock iNLTK to fail
            with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
                mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                # Perform some translations
                await translation_service.translate_text(
                    "Test", LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                # Get stats
                stats = await translation_service.get_translation_stats()
                
                assert isinstance(stats, dict)
                assert "total_cached_translations" in stats
                assert "total_cache_usage" in stats
                assert "cache_hit_rate" in stats
                assert "supported_languages" in stats
                assert "market_terms_count" in stats
                
                # Verify expected values
                assert stats["supported_languages"] == 10
                assert stats["market_terms_count"] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_and_fallbacks(self, translation_service, mock_redis):
        """Test error handling and fallback mechanisms."""
        # Setup cache behavior
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        # Test when all engines fail
        with patch.object(translation_service, '_translate_with_inltk') as mock_inltk:
            mock_inltk.side_effect = RuntimeError("iNLTK failed")
            
            with patch.object(translation_service, '_translate_with_google') as mock_google:
                mock_google.side_effect = RuntimeError("Google failed")
                
                result = await translation_service.translate_text(
                    "Test", LanguageCode.ENGLISH, LanguageCode.HINDI
                )
                
                # Should return original text with zero confidence
                assert result.translated_text == "Test"
                assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_language_detection_integration(self, translation_service):
        """Test language detection integration."""
        # Test with various texts
        test_cases = [
            ("Hello world", LanguageCode.ENGLISH),
            ("", LanguageCode.ENGLISH),  # Empty text should default to English
        ]
        
        for text, expected_default in test_cases:
            result = await translation_service.detect_language(text)
            
            assert hasattr(result, 'detected_language')
            assert hasattr(result, 'confidence_score')
            assert hasattr(result, 'processing_time_ms')
            
            if not text:  # Empty text
                assert result.detected_language == expected_default
                assert result.confidence_score == 0.0
            else:
                assert isinstance(result.detected_language, LanguageCode)
                assert 0.0 <= result.confidence_score <= 1.0