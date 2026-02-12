"""
Language detection utilities for Indian languages.
"""

import time
from typing import Dict, List
import asyncio
from langdetect import detect, detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

from .models import LanguageCode, LanguageDetectionResult


class LanguageDetector:
    """Language detection service for Indian languages."""
    
    # Language code mapping from langdetect to our LanguageCode enum
    LANGUAGE_MAPPING = {
        "hi": LanguageCode.HINDI,
        "en": LanguageCode.ENGLISH,
        "ta": LanguageCode.TAMIL,
        "te": LanguageCode.TELUGU,
        "bn": LanguageCode.BENGALI,
        "mr": LanguageCode.MARATHI,
        "gu": LanguageCode.GUJARATI,
        "kn": LanguageCode.KANNADA,
        "ml": LanguageCode.MALAYALAM,
        "pa": LanguageCode.PUNJABI,
    }
    
    # Fallback patterns for common Indian language words/phrases
    LANGUAGE_PATTERNS = {
        LanguageCode.ENGLISH: ["hello", "thank", "how", "what", "is", "in", "from", "to", "the", "and"],
        LanguageCode.HINDI: ["नमस्ते", "धन्यवाद", "कैसे", "क्या", "है", "में", "से", "को"],
        LanguageCode.TAMIL: ["வணக்கம்", "நன்றி", "எப்படி", "என்ன", "இருக்கிறது", "இல்", "से", "को"],
        LanguageCode.TELUGU: ["నమస్కారం", "ధన్యవాదాలు", "ఎలా", "ఏమిటి", "ఉంది", "లో", "నుండి", "కు"],
        LanguageCode.BENGALI: ["নমস্কার", "ধন্যবাদ", "কেমন", "কি", "আছে", "মধ্যে", "থেকে", "কে"],
        LanguageCode.MARATHI: ["नमस्कार", "धन्यवाद", "कसे", "काय", "आहे", "मध्ये", "पासून", "ला"],
        LanguageCode.GUJARATI: ["નમસ્તે", "આભાર", "કેવી રીતે", "શું", "છે", "માં", "થી", "ને"],
        LanguageCode.KANNADA: ["ನಮಸ್ಕಾರ", "ಧನ್ಯವಾದ", "ಹೇಗೆ", "ಏನು", "ಇದೆ", "ನಲ್ಲಿ", "ಇಂದ", "ಗೆ"],
        LanguageCode.MALAYALAM: ["നമസ്കാരം", "നന്ദി", "എങ്ങനെ", "എന്താണ്", "ഉണ്ട്", "ൽ", "നിന്ന്", "ക്ക്"],
        LanguageCode.PUNJABI: ["ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "ਧੰਨਵਾਦ", "ਕਿਵੇਂ", "ਕੀ", "ਹੈ", "ਵਿੱਚ", "ਤੋਂ", "ਨੂੰ"],
    }
    
    def __init__(self):
        """Initialize the language detector."""
        # Set seed for consistent results
        DetectorFactory.seed = 0
        
    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            LanguageDetectionResult with detected language and confidence
        """
        start_time = time.time()
        
        if not text or not text.strip():
            # Default to English for empty text
            return LanguageDetectionResult(
                detected_language=LanguageCode.ENGLISH,
                confidence_score=0.0,
                all_candidates={"en": 0.0},
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            # Run detection in thread pool to avoid blocking
            detected_lang, all_candidates = await asyncio.get_event_loop().run_in_executor(
                None, self._detect_with_fallback, text
            )
            
            # Map to our language codes
            mapped_lang = self.LANGUAGE_MAPPING.get(detected_lang, LanguageCode.ENGLISH)
            
            # Get confidence score
            confidence = all_candidates.get(detected_lang, 0.0)
            
            return LanguageDetectionResult(
                detected_language=mapped_lang,
                confidence_score=confidence,
                all_candidates=all_candidates,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            # Fallback to pattern matching
            pattern_lang = self._detect_by_patterns(text)
            
            return LanguageDetectionResult(
                detected_language=pattern_lang,
                confidence_score=0.5,  # Medium confidence for pattern matching
                all_candidates={pattern_lang.value: 0.5},
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def _detect_with_fallback(self, text: str) -> tuple[str, Dict[str, float]]:
        """
        Detect language with fallback mechanisms.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (detected_language, all_candidates_dict)
        """
        try:
            # Primary detection
            detected = detect(text)
            
            # Get all candidates with probabilities
            candidates = detect_langs(text)
            all_candidates = {lang.lang: lang.prob for lang in candidates}
            
            return detected, all_candidates
            
        except LangDetectException:
            # Fallback to pattern matching
            pattern_lang = self._detect_by_patterns(text)
            return pattern_lang.value, {pattern_lang.value: 0.5}
    
    def _detect_by_patterns(self, text: str) -> LanguageCode:
        """
        Detect language using pattern matching as fallback.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected LanguageCode
        """
        text_lower = text.lower()
        scores = {}
        
        for lang_code, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    score += 1
            scores[lang_code] = score
        
        # Return language with highest pattern matches
        if scores and max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # Default to English if no patterns match
        return LanguageCode.ENGLISH
    
    def is_supported_language(self, lang_code: str) -> bool:
        """
        Check if a language code is supported.
        
        Args:
            lang_code: Language code to check
            
        Returns:
            True if supported, False otherwise
        """
        return lang_code in [lang.value for lang in LanguageCode]
    
    def get_supported_languages(self) -> List[LanguageCode]:
        """
        Get list of all supported languages.
        
        Returns:
            List of supported LanguageCode values
        """
        return list(LanguageCode)