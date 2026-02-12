"""
Unit tests for language detector.
"""

import pytest
from unittest.mock import patch, Mock

from mandi_platform.translation.language_detector import LanguageDetector
from mandi_platform.translation.models import LanguageCode, LanguageDetectionResult


class TestLanguageDetector:
    """Test cases for LanguageDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a language detector instance for testing."""
        return LanguageDetector()
    
    def test_initialization(self, detector):
        """Test language detector initialization."""
        assert detector is not None
        assert hasattr(detector, 'LANGUAGE_MAPPING')
        assert hasattr(detector, 'LANGUAGE_PATTERNS')
    
    def test_language_mapping_completeness(self, detector):
        """Test that language mapping covers all supported languages."""
        supported_langs = {lang.value for lang in LanguageCode}
        mapped_langs = set(detector.LANGUAGE_MAPPING.keys())
        
        # All supported languages should be in mapping
        assert supported_langs.issubset(mapped_langs)
    
    def test_language_patterns_completeness(self, detector):
        """Test that language patterns are defined for all supported languages."""
        supported_langs = set(LanguageCode)
        pattern_langs = set(detector.LANGUAGE_PATTERNS.keys())
        
        assert supported_langs == pattern_langs
    
    def test_is_supported_language(self, detector):
        """Test language support checking."""
        # Test supported languages
        assert detector.is_supported_language("en") == True
        assert detector.is_supported_language("hi") == True
        assert detector.is_supported_language("ta") == True
        
        # Test unsupported languages
        assert detector.is_supported_language("fr") == False
        assert detector.is_supported_language("de") == False
        assert detector.is_supported_language("") == False
    
    def test_get_supported_languages(self, detector):
        """Test getting list of supported languages."""
        supported = detector.get_supported_languages()
        
        assert isinstance(supported, list)
        assert len(supported) == 10  # We support 10 languages
        assert all(isinstance(lang, LanguageCode) for lang in supported)
        assert LanguageCode.ENGLISH in supported
        assert LanguageCode.HINDI in supported
    
    @pytest.mark.asyncio
    async def test_detect_empty_text(self, detector):
        """Test detection with empty text."""
        result = await detector.detect_language("")
        
        assert isinstance(result, LanguageDetectionResult)
        assert result.detected_language == LanguageCode.ENGLISH
        assert result.confidence_score == 0.0
        assert result.processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_detect_whitespace_text(self, detector):
        """Test detection with whitespace-only text."""
        result = await detector.detect_language("   \n\t  ")
        
        assert isinstance(result, LanguageDetectionResult)
        assert result.detected_language == LanguageCode.ENGLISH
        assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_detect_with_successful_langdetect(self, detector):
        """Test detection when langdetect works successfully."""
        with patch('mandi_platform.translation.language_detector.detect') as mock_detect:
            with patch('mandi_platform.translation.language_detector.detect_langs') as mock_detect_langs:
                # Mock successful detection
                mock_detect.return_value = "en"
                mock_lang = Mock()
                mock_lang.lang = "en"
                mock_lang.prob = 0.9
                mock_detect_langs.return_value = [mock_lang]
                
                result = await detector.detect_language("Hello world")
                
                assert result.detected_language == LanguageCode.ENGLISH
                assert result.confidence_score == 0.9
                assert "en" in result.all_candidates
                mock_detect.assert_called_once_with("Hello world")
                mock_detect_langs.assert_called_once_with("Hello world")
    
    @pytest.mark.asyncio
    async def test_detect_with_langdetect_exception(self, detector):
        """Test detection when langdetect raises exception."""
        with patch('mandi_platform.translation.language_detector.detect') as mock_detect:
            from langdetect.lang_detect_exception import LangDetectException
            mock_detect.side_effect = LangDetectException("Detection failed", "error")
            
            # Mock pattern detection
            with patch.object(detector, '_detect_by_patterns') as mock_pattern:
                mock_pattern.return_value = LanguageCode.HINDI
                
                result = await detector.detect_language("Some text")
                
                assert result.detected_language == LanguageCode.HINDI
                assert result.confidence_score == 0.5  # Pattern matching confidence
                mock_pattern.assert_called_once_with("Some text")
    
    @pytest.mark.asyncio
    async def test_detect_with_general_exception(self, detector):
        """Test detection when general exception occurs."""
        with patch('mandi_platform.translation.language_detector.detect') as mock_detect:
            mock_detect.side_effect = Exception("General error")
            
            # Mock pattern detection
            with patch.object(detector, '_detect_by_patterns') as mock_pattern:
                mock_pattern.return_value = LanguageCode.TAMIL
                
                result = await detector.detect_language("Some text")
                
                assert result.detected_language == LanguageCode.TAMIL
                assert result.confidence_score == 0.5
    
    def test_detect_by_patterns_hindi(self, detector):
        """Test pattern-based detection for Hindi."""
        hindi_text = "नमस्ते, आप कैसे हैं?"
        result = detector._detect_by_patterns(hindi_text)
        
        assert result == LanguageCode.HINDI
    
    def test_detect_by_patterns_tamil(self, detector):
        """Test pattern-based detection for Tamil."""
        tamil_text = "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?"
        result = detector._detect_by_patterns(tamil_text)
        
        assert result == LanguageCode.TAMIL
    
    def test_detect_by_patterns_no_match(self, detector):
        """Test pattern-based detection with no matches."""
        # Text with no recognizable patterns
        result = detector._detect_by_patterns("xyz123")
        
        # Should default to English
        assert result == LanguageCode.ENGLISH
    
    def test_detect_by_patterns_multiple_matches(self, detector):
        """Test pattern-based detection with multiple language matches."""
        # Mix Hindi and English words
        mixed_text = "Hello नमस्ते world"
        result = detector._detect_by_patterns(mixed_text)
        
        # Should return one of the detected languages
        assert isinstance(result, LanguageCode)
    
    def test_detect_with_fallback_successful_detection(self, detector):
        """Test _detect_with_fallback with successful detection."""
        with patch('mandi_platform.translation.language_detector.detect') as mock_detect:
            with patch('mandi_platform.translation.language_detector.detect_langs') as mock_detect_langs:
                mock_detect.return_value = "hi"
                mock_lang = Mock()
                mock_lang.lang = "hi"
                mock_lang.prob = 0.8
                mock_detect_langs.return_value = [mock_lang]
                
                detected, candidates = detector._detect_with_fallback("नमस्ते")
                
                assert detected == "hi"
                assert candidates == {"hi": 0.8}
    
    def test_detect_with_fallback_exception(self, detector):
        """Test _detect_with_fallback with exception."""
        with patch('mandi_platform.translation.language_detector.detect') as mock_detect:
            from langdetect.lang_detect_exception import LangDetectException
            mock_detect.side_effect = LangDetectException("Error", "code")
            
            with patch.object(detector, '_detect_by_patterns') as mock_pattern:
                mock_pattern.return_value = LanguageCode.BENGALI
                
                detected, candidates = detector._detect_with_fallback("Some text")
                
                assert detected == "bn"
                assert candidates == {"bn": 0.5}


class TestLanguageDetectorIntegration:
    """Integration tests for language detector."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_detection_english(self):
        """Test real detection with English text."""
        detector = LanguageDetector()
        
        result = await detector.detect_language("Hello, how are you today?")
        
        assert isinstance(result, LanguageDetectionResult)
        assert result.detected_language in [LanguageCode.ENGLISH]  # Should detect English
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.processing_time_ms > 0
        assert isinstance(result.all_candidates, dict)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_detection_hindi(self):
        """Test real detection with Hindi text."""
        detector = LanguageDetector()
        
        result = await detector.detect_language("नमस्ते, आप कैसे हैं?")
        
        assert isinstance(result, LanguageDetectionResult)
        # Should detect Hindi or fall back to pattern matching
        assert isinstance(result.detected_language, LanguageCode)
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_detection_mixed_content(self):
        """Test real detection with mixed language content."""
        detector = LanguageDetector()
        
        # Mix of English and Hindi
        result = await detector.detect_language("Hello नमस्ते world")
        
        assert isinstance(result, LanguageDetectionResult)
        assert isinstance(result.detected_language, LanguageCode)
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_detection_numbers_and_symbols(self):
        """Test real detection with numbers and symbols."""
        detector = LanguageDetector()
        
        result = await detector.detect_language("123 ₹500 @#$%")
        
        assert isinstance(result, LanguageDetectionResult)
        # Should default to English for non-linguistic content
        assert result.detected_language == LanguageCode.ENGLISH
        assert result.processing_time_ms > 0