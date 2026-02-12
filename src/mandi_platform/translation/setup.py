"""
Setup and testing utilities for Indian language NLP libraries.
"""

import asyncio
import logging
from typing import Dict, Any

from .config import NLPLibraryConfig, initialize_nlp_libraries
from .service import TranslationService
from .models import LanguageCode

logger = logging.getLogger(__name__)


async def setup_and_test_libraries() -> Dict[str, Any]:
    """
    Set up and test all NLP libraries.
    
    Returns:
        Dictionary with setup and test results
    """
    results = {
        "library_status": {},
        "translation_tests": {},
        "language_detection_tests": {},
        "errors": []
    }
    
    try:
        # Initialize libraries
        logger.info("Setting up NLP libraries...")
        results["library_status"] = initialize_nlp_libraries()
        
        # Test translation service
        logger.info("Testing translation service...")
        translation_service = TranslationService()
        
        # Test language detection
        test_texts = {
            "en": "Hello, how are you?",
            "hi": "नमस्ते, आप कैसे हैं?",
            "ta": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?",
            "te": "నమస్కారం, మీరు ఎలా ఉన్నారు?",
            "bn": "নমস্কার, আপনি কেমন আছেন?",
        }
        
        for lang_code, text in test_texts.items():
            try:
                detection_result = await translation_service.detect_language(text)
                results["language_detection_tests"][lang_code] = {
                    "text": text,
                    "detected": detection_result.detected_language.value,
                    "confidence": detection_result.confidence_score,
                    "success": detection_result.detected_language.value == lang_code
                }
            except Exception as e:
                results["language_detection_tests"][lang_code] = {
                    "text": text,
                    "error": str(e),
                    "success": False
                }
                results["errors"].append(f"Language detection failed for {lang_code}: {e}")
        
        # Test translations
        test_translations = [
            ("Hello", LanguageCode.ENGLISH, LanguageCode.HINDI),
            ("Thank you", LanguageCode.ENGLISH, LanguageCode.TAMIL),
            ("Good morning", LanguageCode.ENGLISH, LanguageCode.BENGALI),
        ]
        
        for text, source_lang, target_lang in test_translations:
            test_key = f"{source_lang.value}_to_{target_lang.value}"
            try:
                translation_result = await translation_service.translate_text(
                    text, source_lang, target_lang
                )
                results["translation_tests"][test_key] = {
                    "source_text": text,
                    "translated_text": translation_result.translated_text,
                    "confidence": translation_result.confidence_score,
                    "engine": translation_result.engine_used.value,
                    "success": translation_result.confidence_score > 0.0
                }
            except Exception as e:
                results["translation_tests"][test_key] = {
                    "source_text": text,
                    "error": str(e),
                    "success": False
                }
                results["errors"].append(f"Translation failed for {test_key}: {e}")
        
        logger.info("NLP library setup and testing completed")
        
    except Exception as e:
        error_msg = f"Setup and testing failed: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    return results


def print_setup_results(results: Dict[str, Any]):
    """Print setup results in a readable format."""
    print("\n" + "="*60)
    print("INDIAN LANGUAGE NLP LIBRARIES SETUP RESULTS")
    print("="*60)
    
    # Library status
    print("\n📚 LIBRARY STATUS:")
    for library, status in results["library_status"].items():
        available = "✅" if status["available"] else "❌"
        print(f"  {available} {library.upper()}: {'Available' if status['available'] else 'Not Available'}")
        
        if library == "inltk" and status["available"]:
            print("    Models:")
            for lang, model_status in status.get("models", {}).items():
                model_icon = "✅" if model_status else "❌"
                print(f"      {model_icon} {lang}")
        
        elif library == "indic_nlp" and status["available"]:
            resources_icon = "✅" if status.get("resources", False) else "❌"
            print(f"    {resources_icon} Resources configured")
        
        elif library == "google_translate" and status["available"]:
            api_icon = "✅" if status.get("api_working", False) else "❌"
            print(f"    {api_icon} API working")
    
    # Language detection tests
    print("\n🔍 LANGUAGE DETECTION TESTS:")
    for lang_code, test_result in results["language_detection_tests"].items():
        success_icon = "✅" if test_result["success"] else "❌"
        if "error" in test_result:
            print(f"  {success_icon} {lang_code.upper()}: ERROR - {test_result['error']}")
        else:
            detected = test_result["detected"]
            confidence = test_result["confidence"]
            print(f"  {success_icon} {lang_code.upper()}: Detected as {detected} (confidence: {confidence:.2f})")
    
    # Translation tests
    print("\n🔄 TRANSLATION TESTS:")
    for test_key, test_result in results["translation_tests"].items():
        success_icon = "✅" if test_result["success"] else "❌"
        if "error" in test_result:
            print(f"  {success_icon} {test_key}: ERROR - {test_result['error']}")
        else:
            source = test_result["source_text"]
            translated = test_result["translated_text"]
            engine = test_result["engine"]
            confidence = test_result["confidence"]
            print(f"  {success_icon} {test_key}: '{source}' → '{translated}' (engine: {engine}, confidence: {confidence:.2f})")
    
    # Errors
    if results["errors"]:
        print("\n❌ ERRORS:")
        for error in results["errors"]:
            print(f"  • {error}")
    
    print("\n" + "="*60)


async def main():
    """Main function for running setup and tests."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run setup and tests
    results = await setup_and_test_libraries()
    
    # Print results
    print_setup_results(results)
    
    # Return success status
    has_errors = bool(results["errors"])
    return not has_errors


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)