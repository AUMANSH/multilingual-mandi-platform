"""
Configuration utilities for Indian language NLP libraries.
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NLPLibraryConfig:
    """Configuration manager for Indian language NLP libraries."""
    
    # Supported languages with their configurations
    LANGUAGE_CONFIGS = {
        "hi": {
            "name": "Hindi",
            "script": "Devanagari",
            "inltk_code": "hi",
            "google_code": "hi",
            "indic_nlp_code": "hi",
        },
        "en": {
            "name": "English",
            "script": "Latin",
            "inltk_code": "en",
            "google_code": "en",
            "indic_nlp_code": "en",
        },
        "ta": {
            "name": "Tamil",
            "script": "Tamil",
            "inltk_code": "ta",
            "google_code": "ta",
            "indic_nlp_code": "ta",
        },
        "te": {
            "name": "Telugu",
            "script": "Telugu",
            "inltk_code": "te",
            "google_code": "te",
            "indic_nlp_code": "te",
        },
        "bn": {
            "name": "Bengali",
            "script": "Bengali",
            "inltk_code": "bn",
            "google_code": "bn",
            "indic_nlp_code": "bn",
        },
        "mr": {
            "name": "Marathi",
            "script": "Devanagari",
            "inltk_code": "mr",
            "google_code": "mr",
            "indic_nlp_code": "mr",
        },
        "gu": {
            "name": "Gujarati",
            "script": "Gujarati",
            "inltk_code": "gu",
            "google_code": "gu",
            "indic_nlp_code": "gu",
        },
        "kn": {
            "name": "Kannada",
            "script": "Kannada",
            "inltk_code": "kn",
            "google_code": "kn",
            "indic_nlp_code": "kn",
        },
        "ml": {
            "name": "Malayalam",
            "script": "Malayalam",
            "inltk_code": "ml",
            "google_code": "ml",
            "indic_nlp_code": "ml",
        },
        "pa": {
            "name": "Punjabi",
            "script": "Gurmukhi",
            "inltk_code": "pa",
            "google_code": "pa",
            "indic_nlp_code": "pa",
        },
    }
    
    @classmethod
    def get_language_config(cls, lang_code: str) -> Optional[Dict]:
        """Get configuration for a specific language."""
        return cls.LANGUAGE_CONFIGS.get(lang_code)
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Get list of supported language codes."""
        return list(cls.LANGUAGE_CONFIGS.keys())
    
    @classmethod
    def is_supported(cls, lang_code: str) -> bool:
        """Check if a language is supported."""
        return lang_code in cls.LANGUAGE_CONFIGS
    
    @classmethod
    def get_script_for_language(cls, lang_code: str) -> Optional[str]:
        """Get script name for a language."""
        config = cls.get_language_config(lang_code)
        return config["script"] if config else None
    
    @classmethod
    def setup_inltk_models(cls) -> Dict[str, bool]:
        """
        Set up iNLTK models for all supported languages.
        
        Returns:
            Dictionary mapping language codes to setup success status
        """
        setup_status = {}
        
        try:
            from inltk import inltk
            
            for lang_code, config in cls.LANGUAGE_CONFIGS.items():
                if lang_code == "en":  # Skip English for iNLTK
                    setup_status[lang_code] = True
                    continue
                
                try:
                    inltk_code = config["inltk_code"]
                    inltk.setup(inltk_code)
                    setup_status[lang_code] = True
                    logger.info(f"Successfully set up iNLTK model for {config['name']}")
                except Exception as e:
                    setup_status[lang_code] = False
                    logger.warning(f"Failed to set up iNLTK model for {config['name']}: {e}")
                    
        except ImportError:
            logger.warning("iNLTK not available")
            setup_status = {lang: False for lang in cls.LANGUAGE_CONFIGS.keys()}
        
        return setup_status
    
    @classmethod
    def setup_indic_nlp_resources(cls, resources_path: Optional[str] = None) -> bool:
        """
        Set up Indic NLP Library resources.
        
        Args:
            resources_path: Path to Indic NLP resources directory
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            from indic_nlp_library import common
            
            if resources_path is None:
                # Try to find resources in common locations
                possible_paths = [
                    "indic_nlp_resources",
                    "/usr/local/share/indic_nlp_resources",
                    os.path.expanduser("~/indic_nlp_resources"),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        resources_path = path
                        break
                else:
                    logger.warning("Indic NLP resources not found in common locations")
                    return False
            
            common.set_resources_path(resources_path)
            logger.info(f"Successfully set up Indic NLP Library with resources at {resources_path}")
            return True
            
        except ImportError:
            logger.warning("Indic NLP Library not available")
            return False
        except Exception as e:
            logger.warning(f"Failed to set up Indic NLP Library: {e}")
            return False
    
    @classmethod
    def validate_google_translate_setup(cls, api_key: Optional[str] = None) -> bool:
        """
        Validate Google Translate API setup.
        
        Args:
            api_key: Google Translate API key (optional)
            
        Returns:
            True if setup is valid, False otherwise
        """
        try:
            from googletrans import Translator
            
            translator = Translator()
            
            # Test with a simple translation (synchronous)
            result = translator.translate("Hello", src="en", dest="hi")
            
            if result and hasattr(result, 'text') and result.text:
                logger.info("Google Translate API is working")
                return True
            else:
                logger.warning("Google Translate API test failed - no result")
                return False
                
        except ImportError:
            logger.warning("Google Translate library not available")
            return False
        except Exception as e:
            logger.warning(f"Google Translate API validation failed: {e}")
            return False
    
    @classmethod
    def get_library_status(cls) -> Dict[str, Dict[str, bool]]:
        """
        Get status of all NLP libraries.
        
        Returns:
            Dictionary with library status information
        """
        status = {
            "inltk": {"available": False, "models": {}},
            "indic_nlp": {"available": False, "resources": False},
            "google_translate": {"available": False, "api_working": False},
        }
        
        # Check iNLTK
        try:
            import inltk
            status["inltk"]["available"] = True
            status["inltk"]["models"] = cls.setup_inltk_models()
        except ImportError:
            pass
        
        # Check Indic NLP Library
        try:
            from indic_nlp_library import common
            status["indic_nlp"]["available"] = True
            status["indic_nlp"]["resources"] = cls.setup_indic_nlp_resources()
        except ImportError:
            pass
        
        # Check Google Translate
        try:
            from googletrans import Translator
            status["google_translate"]["available"] = True
            status["google_translate"]["api_working"] = cls.validate_google_translate_setup()
        except ImportError:
            pass
        
        return status


def initialize_nlp_libraries() -> Dict[str, Dict[str, bool]]:
    """
    Initialize all NLP libraries and return status.
    
    Returns:
        Dictionary with initialization status for all libraries
    """
    logger.info("Initializing Indian language NLP libraries...")
    
    config = NLPLibraryConfig()
    status = config.get_library_status()
    
    # Log status
    for library, lib_status in status.items():
        if lib_status["available"]:
            logger.info(f"{library} is available")
        else:
            logger.warning(f"{library} is not available")
    
    return status