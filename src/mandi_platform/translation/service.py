"""
Translation service implementation using multiple NLP libraries.
"""

import time
import hashlib
import asyncio
import json
from typing import Optional, Dict, Any, List
import logging

# Indian language libraries
try:
    from inltk import inltk
except ImportError:
    inltk = None

try:
    from googletrans import Translator as GoogleTranslator
except ImportError:
    GoogleTranslator = None

try:
    from indic_nlp_library import common
    from indic_nlp_library.tokenize import indic_tokenize
    from indic_nlp_library.normalize import indic_normalize
except ImportError:
    common = None
    indic_tokenize = None
    indic_normalize = None

from ..config import settings
from ..redis_client import get_redis_client
from .models import (
    LanguageCode,
    TranslationEngine,
    TranslationResult,
    ContextualTranslationResult,
    MarketContext,
    TranslationCache,
)
from .language_detector import LanguageDetector

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translation service supporting multiple Indian languages.
    
    Uses iNLTK as primary engine with Google Translate as fallback.
    Includes caching and market context preservation.
    """
    
    # Market-specific terminology that should be preserved
    MARKET_TERMS = {
        "en": ["mandi", "quintal", "rate", "bhav", "arrival", "quality", "grade"],
        "hi": ["मंडी", "क्विंटल", "रेट", "भाव", "आवक", "गुणवत्ता", "ग्रेड"],
        "ta": ["மண்டி", "குவிண்டல்", "விலை", "பாவ்", "வருகை", "தரம்", "கிரேட்"],
        "te": ["మండి", "క్వింటల్", "రేట్", "భావ్", "రాక", "నాణ్యత", "గ్రేడ్"],
        "bn": ["মান্ডি", "কুইন্টাল", "রেট", "ভাব", "আগমন", "গুণমান", "গ্রেড"],
        "mr": ["मंडी", "क्विंटल", "रेट", "भाव", "आगमन", "गुणवत्ता", "ग्रेड"],
        "gu": ["મંડી", "ક્વિંટલ", "રેટ", "ભાવ", "આગમન", "ગુણવત્તા", "ગ્રેડ"],
        "kn": ["ಮಂಡಿ", "ಕ್ವಿಂಟಲ್", "ರೇಟ್", "ಭಾವ್", "ಆಗಮನ", "ಗುಣಮಟ್ಟ", "ಗ್ರೇಡ್"],
        "ml": ["മണ്ടി", "ക്വിന്റൽ", "റേറ്റ്", "ഭാവ്", "വരവ്", "ഗുണനിലവാരം", "ഗ്രേഡ്"],
        "pa": ["ਮੰਡੀ", "ਕੁਇੰਟਲ", "ਰੇਟ", "ਭਾਵ", "ਆਮਦ", "ਗੁਣਵੱਤਾ", "ਗ੍ਰੇਡ"],
    }
    
    # iNLTK language code mapping
    INLTK_LANGUAGE_MAPPING = {
        LanguageCode.HINDI: "hi",
        LanguageCode.ENGLISH: "en",
        LanguageCode.TAMIL: "ta",
        LanguageCode.TELUGU: "te",
        LanguageCode.BENGALI: "bn",
        LanguageCode.MARATHI: "mr",
        LanguageCode.GUJARATI: "gu",
        LanguageCode.KANNADA: "kn",
        LanguageCode.MALAYALAM: "ml",
        LanguageCode.PUNJABI: "pa",
    }
    
    def __init__(self):
        """Initialize the translation service."""
        self.language_detector = LanguageDetector()
        self.google_translator = None
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize translation engines."""
        # Initialize Google Translate if API key is available
        if settings.google_translate_api_key and GoogleTranslator:
            try:
                self.google_translator = GoogleTranslator()
                logger.info("Google Translate initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Translate: {e}")
        
        # Initialize iNLTK
        if inltk:
            try:
                # Download models for supported languages (this is idempotent)
                for lang_code in self.INLTK_LANGUAGE_MAPPING.values():
                    if lang_code != "en":  # English doesn't need iNLTK model
                        try:
                            inltk.setup(lang_code)
                        except Exception as e:
                            logger.warning(f"Failed to setup iNLTK for {lang_code}: {e}")
                logger.info("iNLTK initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize iNLTK: {e}")
        
        # Initialize Indic NLP Library
        if common:
            try:
                # Set up Indic NLP Library path (this might need adjustment based on installation)
                common.set_resources_path("indic_nlp_resources")
                logger.info("Indic NLP Library initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Indic NLP Library: {e}")
    
    async def translate_text(
        self,
        text: str,
        source_lang: LanguageCode,
        target_lang: LanguageCode,
        context: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate text between supported languages.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context for better translation
            
        Returns:
            TranslationResult with translation details
        """
        start_time = time.time()
        
        # Validate inputs
        if not text or not text.strip():
            return TranslationResult(
                translated_text="",
                source_language=source_lang,
                target_language=target_lang,
                confidence_score=1.0,
                engine_used=TranslationEngine.INLTK,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        text = text.strip()
        
        # Check cache first
        cache_key = self._get_cache_key(text, source_lang, target_lang, context)
        cached_result = await self._get_cached_translation(cache_key)
        
        if cached_result:
            cached_result.cached = True
            cached_result.processing_time_ms = (time.time() - start_time) * 1000
            return cached_result
        
        # If source and target are the same, return original text
        if source_lang == target_lang:
            result = TranslationResult(
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence_score=1.0,
                engine_used=TranslationEngine.INLTK,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            await self._cache_translation(cache_key, result)
            return result
        
        # Try translation engines in order of preference
        engines = [
            (TranslationEngine.INLTK, self._translate_with_inltk),
            (TranslationEngine.GOOGLE_TRANSLATE, self._translate_with_google),
        ]
        
        last_error = None
        for engine, translate_func in engines:
            try:
                translated_text, base_confidence = await translate_func(
                    text, source_lang, target_lang
                )
                
                # Calculate adjusted confidence score
                confidence = self._calculate_confidence_score(
                    text, translated_text, engine, base_confidence
                )
                
                result = TranslationResult(
                    translated_text=translated_text,
                    source_language=source_lang,
                    target_language=target_lang,
                    confidence_score=confidence,
                    engine_used=engine,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
                
                # Cache successful translation
                await self._cache_translation(cache_key, result)
                return result
                
            except Exception as e:
                logger.warning(f"Translation failed with {engine}: {e}")
                last_error = e
                continue
        
        # If all engines fail, return original text with low confidence
        logger.error(f"All translation engines failed. Last error: {last_error}")
        result = TranslationResult(
            translated_text=text,
            source_language=source_lang,
            target_language=target_lang,
            confidence_score=0.0,
            engine_used=TranslationEngine.INLTK,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        return result
    
    async def translate_with_context(
        self,
        text: str,
        source_lang: LanguageCode,
        target_lang: LanguageCode,
        market_context: MarketContext
    ) -> ContextualTranslationResult:
        """
        Translate text with market context preservation.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            market_context: Market context for better translation
            
        Returns:
            ContextualTranslationResult with context-aware translation
        """
        # First, perform regular translation
        base_result = await self.translate_text(
            text, source_lang, target_lang, str(market_context)
        )
        
        # Preserve market terms
        preserved_terms = self._preserve_market_terms(
            base_result.translated_text, source_lang, target_lang
        )
        
        # Apply cultural adaptations (placeholder for future enhancement)
        cultural_adaptations = 0
        
        return ContextualTranslationResult(
            translated_text=preserved_terms,
            source_language=source_lang,
            target_language=target_lang,
            confidence_score=base_result.confidence_score,
            engine_used=base_result.engine_used,
            cached=base_result.cached,
            processing_time_ms=base_result.processing_time_ms,
            market_terms_preserved=len(self.MARKET_TERMS.get(source_lang.value, [])),
            cultural_adaptations=cultural_adaptations,
            context_used=market_context
        )
    
    async def detect_language(self, text: str):
        """Detect language of the given text."""
        return await self.language_detector.detect_language(text)
    
    async def translate_batch(
        self,
        texts: List[str],
        source_lang: LanguageCode,
        target_lang: LanguageCode,
        context: Optional[str] = None
    ) -> List[TranslationResult]:
        """
        Translate multiple texts in batch for better performance.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context for better translation
            
        Returns:
            List of TranslationResult objects
        """
        if not texts:
            return []
        
        # Use asyncio.gather for concurrent translation
        tasks = [
            self.translate_text(text, source_lang, target_lang, context)
            for text in texts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch translation failed for text {i}: {result}")
                # Return a failed translation result
                final_results.append(TranslationResult(
                    translated_text=texts[i],
                    source_language=source_lang,
                    target_language=target_lang,
                    confidence_score=0.0,
                    engine_used=TranslationEngine.INLTK,
                    processing_time_ms=0.0
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _translate_with_inltk(
        self, text: str, source_lang: LanguageCode, target_lang: LanguageCode
    ) -> tuple[str, float]:
        """
        Translate using iNLTK with rule-based approach for market terms.
        
        Args:
            text: Text to translate
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            Tuple of (translated_text, confidence_score)
        """
        if not inltk:
            raise RuntimeError("iNLTK not available")
        
        source_code = self.INLTK_LANGUAGE_MAPPING[source_lang]
        target_code = self.INLTK_LANGUAGE_MAPPING[target_lang]
        
        def _translate():
            try:
                # Use iNLTK for text preprocessing and tokenization
                if source_code != "en":
                    # Tokenize using iNLTK for Indian languages
                    tokens = inltk.tokenize(text, source_code)
                else:
                    tokens = text.split()
                
                # Apply rule-based translation for market terms
                translated_tokens = []
                confidence_scores = []
                
                source_terms = self.MARKET_TERMS.get(source_lang.value, [])
                target_terms = self.MARKET_TERMS.get(target_lang.value, [])
                
                # Create term mapping
                term_map = {}
                if len(source_terms) == len(target_terms):
                    term_map = dict(zip(source_terms, target_terms))
                
                for token in tokens:
                    # Check if token is a market term
                    token_lower = token.lower()
                    if token_lower in [term.lower() for term in source_terms]:
                        # Find the matching term with proper case
                        for src_term, tgt_term in term_map.items():
                            if token_lower == src_term.lower():
                                translated_tokens.append(tgt_term)
                                confidence_scores.append(0.95)  # High confidence for market terms
                                break
                    else:
                        # For non-market terms, use simple rule-based approach
                        # This is a placeholder - in practice, you'd use more sophisticated methods
                        translated_tokens.append(token)
                        confidence_scores.append(0.3)  # Low confidence for non-market terms
                
                # Calculate overall confidence
                if confidence_scores:
                    avg_confidence = sum(confidence_scores) / len(confidence_scores)
                else:
                    avg_confidence = 0.1
                
                # Join tokens back
                if target_code != "en" and inltk:
                    # For Indian languages, try to use proper joining
                    translated_text = " ".join(translated_tokens)
                else:
                    translated_text = " ".join(translated_tokens)
                
                # If we have very low confidence, raise error to fallback to Google
                if avg_confidence < 0.4:
                    raise RuntimeError("iNLTK confidence too low, falling back to Google Translate")
                
                return translated_text, avg_confidence
                
            except Exception as e:
                logger.debug(f"iNLTK processing failed: {e}")
                raise
        
        return await asyncio.get_event_loop().run_in_executor(None, _translate)
    
    async def _translate_with_google(
        self, text: str, source_lang: LanguageCode, target_lang: LanguageCode
    ) -> tuple[str, float]:
        """
        Translate using Google Translate.
        
        Args:
            text: Text to translate
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            Tuple of (translated_text, confidence_score)
        """
        if not self.google_translator:
            raise RuntimeError("Google Translate not available")
        
        def _translate():
            try:
                result = self.google_translator.translate(
                    text,
                    src=source_lang.value,
                    dest=target_lang.value
                )
                # Handle both sync and async results
                if hasattr(result, 'text'):
                    translated_text = result.text
                    confidence = getattr(result, 'confidence', 0.9)
                    return translated_text, confidence
                else:
                    raise RuntimeError("Invalid translation result")
            except Exception as e:
                logger.error(f"Google Translate error: {e}")
                raise
        
        # Run in thread pool to avoid blocking
        translated, confidence = await asyncio.get_event_loop().run_in_executor(
            None, _translate
        )
        return translated, confidence
    
    def _preserve_market_terms(
        self, text: str, source_lang: LanguageCode, target_lang: LanguageCode
    ) -> str:
        """
        Preserve market-specific terminology in translation.
        
        Args:
            text: Translated text
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            Text with preserved market terms
        """
        source_terms = self.MARKET_TERMS.get(source_lang.value, [])
        target_terms = self.MARKET_TERMS.get(target_lang.value, [])
        
        # Create term mapping
        if len(source_terms) != len(target_terms):
            logger.warning(f"Market term count mismatch: {source_lang.value} vs {target_lang.value}")
            return text
        
        term_map = dict(zip(source_terms, target_terms))
        preserved_text = text
        
        # Replace terms with case-sensitive matching
        for source_term, target_term in term_map.items():
            # Handle different cases
            replacements = [
                (source_term.lower(), target_term.lower()),
                (source_term.upper(), target_term.upper()),
                (source_term.title(), target_term.title()),
                (source_term, target_term),  # Original case
            ]
            
            for src, tgt in replacements:
                if src in preserved_text:
                    preserved_text = preserved_text.replace(src, tgt)
        
        # Also handle partial matches and plurals
        for source_term, target_term in term_map.items():
            # Handle plurals (simple approach)
            if source_term.endswith('s'):
                plural_src = source_term
                plural_tgt = target_term + 's' if not target_term.endswith('s') else target_term
            else:
                plural_src = source_term + 's'
                plural_tgt = target_term + 's' if not target_term.endswith('s') else target_term
            
            preserved_text = preserved_text.replace(plural_src, plural_tgt)
        
        return preserved_text
    
    def _calculate_confidence_score(
        self, 
        original_text: str, 
        translated_text: str, 
        engine: TranslationEngine,
        base_confidence: float = 0.8
    ) -> float:
        """
        Calculate confidence score for translation.
        
        Args:
            original_text: Original text
            translated_text: Translated text
            engine: Translation engine used
            base_confidence: Base confidence from engine
            
        Returns:
            Adjusted confidence score
        """
        confidence = base_confidence
        
        # Adjust based on text length
        if len(original_text) < 5:
            confidence *= 0.8  # Lower confidence for very short text
        elif len(original_text) > 50:
            confidence *= 1.2  # Higher confidence for longer text
        
        # Adjust based on engine
        if engine == TranslationEngine.GOOGLE_TRANSLATE:
            confidence *= 1.0  # Google Translate baseline
        elif engine == TranslationEngine.INLTK:
            confidence *= 0.9  # Slightly lower for iNLTK (rule-based)
        
        # Check for market terms presence
        market_terms_found = 0
        for lang_terms in self.MARKET_TERMS.values():
            for term in lang_terms:
                if term.lower() in original_text.lower():
                    market_terms_found += 1
        
        if market_terms_found > 0:
            confidence *= 1.1  # Higher confidence when market terms are present
        
        # Ensure confidence is within bounds
        return min(max(confidence, 0.0), 1.0)
    
    def _get_cache_key(
        self,
        text: str,
        source_lang: LanguageCode,
        target_lang: LanguageCode,
        context: Optional[str] = None
    ) -> str:
        """Generate cache key for translation."""
        content = f"{text}:{source_lang.value}:{target_lang.value}:{context or ''}"
        return f"translation:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _get_cached_translation(self, cache_key: str) -> Optional[TranslationResult]:
        """Get cached translation result."""
        try:
            redis = await get_redis_client()
            cached_data = await redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return TranslationResult(**data)
        except Exception as e:
            logger.warning(f"Failed to get cached translation: {e}")
        
        return None
    
    async def _cache_translation(self, cache_key: str, result: TranslationResult):
        """Cache translation result."""
        try:
            redis = await get_redis_client()
            data = result.model_dump()
            await redis.setex(
                cache_key,
                settings.translation_cache_ttl,
                json.dumps(data)
            )
            
            # Also increment usage count for analytics
            usage_key = f"{cache_key}:usage"
            await redis.incr(usage_key)
            await redis.expire(usage_key, settings.translation_cache_ttl)
            
        except Exception as e:
            logger.warning(f"Failed to cache translation: {e}")
    
    async def get_translation_stats(self) -> Dict[str, Any]:
        """Get translation service statistics."""
        try:
            redis = await get_redis_client()
            
            # Get cache hit statistics
            cache_keys = []
            try:
                async for key in redis.scan_iter(match="translation:*"):
                    if not key.endswith(":usage"):
                        cache_keys.append(key)
            except Exception as e:
                logger.warning(f"Failed to scan cache keys: {e}")
            
            total_cached = len(cache_keys)
            
            # Get usage statistics
            usage_keys = []
            total_usage = 0
            try:
                async for key in redis.scan_iter(match="translation:*:usage"):
                    usage_count = await redis.get(key)
                    if usage_count:
                        total_usage += int(usage_count)
                        usage_keys.append(key)
            except Exception as e:
                logger.warning(f"Failed to scan usage keys: {e}")
            
            return {
                "total_cached_translations": total_cached,
                "total_cache_usage": total_usage,
                "cache_hit_rate": total_usage / max(total_cached, 1),
                "supported_languages": len(self.INLTK_LANGUAGE_MAPPING),
                "market_terms_count": sum(len(terms) for terms in self.MARKET_TERMS.values())
            }
            
        except Exception as e:
            logger.warning(f"Failed to get translation stats: {e}")
            return {
                "total_cached_translations": 0,
                "total_cache_usage": 0,
                "cache_hit_rate": 0.0,
                "supported_languages": len(self.INLTK_LANGUAGE_MAPPING),
                "market_terms_count": sum(len(terms) for terms in self.MARKET_TERMS.values())
            }