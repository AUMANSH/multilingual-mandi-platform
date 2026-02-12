"""
Property-based tests for language interface completeness.

This module implements Property 2 from the design document:
"For any supported language selection, all user interface elements should be 
displayed in that language, and switching languages should preserve all session 
data and user context."

Validates: Requirements 1.1, 1.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
import json

from mandi_platform.translation.models import LanguageCode
from mandi_platform.translation.service import TranslationService
from tests.utils.generators import (
    supported_languages,
    user_session_data,
    ui_element_keys,
    market_context_data
)


class MockUIElement:
    """Mock UI element for testing interface completeness."""
    
    def __init__(self, key: str, default_text: str, element_type: str = "text"):
        self.key = key
        self.default_text = default_text
        self.element_type = element_type
        self.current_language = LanguageCode.ENGLISH
        self.translated_text = default_text
    
    async def set_language(self, language: LanguageCode, translation_service: TranslationService):
        """Set the language for this UI element."""
        if language == LanguageCode.ENGLISH:
            self.translated_text = self.default_text
        else:
            # Use translation service to translate the element
            result = await translation_service.translate_text(
                self.default_text,
                LanguageCode.ENGLISH,
                language
            )
            self.translated_text = result.translated_text
        
        self.current_language = language
    
    def get_display_text(self) -> str:
        """Get the current display text."""
        return self.translated_text


class MockUserSession:
    """Mock user session for testing session data preservation."""
    
    def __init__(self, session_data: Dict[str, Any]):
        self.data = session_data.copy()
        self.language = session_data.get('preferred_language', LanguageCode.ENGLISH)
        self.original_data = session_data.copy()
    
    def set_language(self, language: LanguageCode):
        """Set the session language."""
        self.language = language
        self.data['preferred_language'] = language
    
    def get_data(self) -> Dict[str, Any]:
        """Get session data."""
        return self.data.copy()
    
    def update_data(self, key: str, value: Any):
        """Update session data."""
        self.data[key] = value
    
    def is_data_preserved(self, exclude_keys: Optional[set] = None) -> bool:
        """Check if session data is preserved (excluding specified keys)."""
        exclude_keys = exclude_keys or {'preferred_language'}
        
        for key, original_value in self.original_data.items():
            if key in exclude_keys:
                continue
            
            current_value = self.data.get(key)
            if current_value != original_value:
                return False
        
        return True


class MockLanguageInterface:
    """Mock language interface system for testing."""
    
    def __init__(self):
        self.translation_service = TranslationService()
        self.ui_elements: Dict[str, MockUIElement] = {}
        self.current_language = LanguageCode.ENGLISH
        self.session: Optional[MockUserSession] = None
    
    def add_ui_element(self, key: str, default_text: str, element_type: str = "text"):
        """Add a UI element to the interface."""
        self.ui_elements[key] = MockUIElement(key, default_text, element_type)
    
    def set_session(self, session: MockUserSession):
        """Set the user session."""
        self.session = session
        self.current_language = session.language
    
    async def switch_language(self, target_language: LanguageCode) -> Dict[str, Any]:
        """
        Switch the interface language and return results.
        
        Returns:
            Dict containing switch results and validation data
        """
        if not self.session:
            raise ValueError("No session set")
        
        # Store original session data for comparison
        original_session_data = self.session.get_data()
        
        # Switch language in session
        self.session.set_language(target_language)
        
        # Translate all UI elements
        translation_results = {}
        translation_errors = []
        
        for key, element in self.ui_elements.items():
            try:
                await element.set_language(target_language, self.translation_service)
                translation_results[key] = {
                    'original_text': element.default_text,
                    'translated_text': element.translated_text,
                    'language': target_language,
                    'success': True
                }
            except Exception as e:
                translation_errors.append({
                    'element_key': key,
                    'error': str(e)
                })
                translation_results[key] = {
                    'original_text': element.default_text,
                    'translated_text': element.default_text,  # Fallback to original
                    'language': target_language,
                    'success': False,
                    'error': str(e)
                }
        
        # Update current language
        self.current_language = target_language
        
        # Check session data preservation
        session_preserved = self.session.is_data_preserved()
        
        return {
            'target_language': target_language,
            'translation_results': translation_results,
            'translation_errors': translation_errors,
            'session_data_preserved': session_preserved,
            'original_session_data': original_session_data,
            'current_session_data': self.session.get_data(),
            'total_elements': len(self.ui_elements),
            'successful_translations': len([r for r in translation_results.values() if r['success']]),
            'failed_translations': len(translation_errors)
        }
    
    def get_all_element_texts(self) -> Dict[str, str]:
        """Get current text for all UI elements."""
        return {key: element.get_display_text() for key, element in self.ui_elements.items()}
    
    def validate_language_consistency(self) -> bool:
        """Validate that all elements are in the current language."""
        for element in self.ui_elements.values():
            if element.current_language != self.current_language:
                return False
        return True


class TestLanguageInterfaceCompleteness:
    """Property-based tests for language interface completeness."""
    
    def get_mock_redis(self):
        """Get a mock Redis client for translation service."""
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None  # No cache hits for testing
        redis_mock.setex = AsyncMock()
        redis_mock.incr = AsyncMock()
        redis_mock.expire = AsyncMock()
        return redis_mock
    
    @given(
        target_language=supported_languages(),
        session_data=user_session_data(),
        ui_elements=ui_element_keys()
    )
    @settings(
        max_examples=100, 
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_language_interface_completeness_property(
        self, 
        target_language: LanguageCode,
        session_data: Dict[str, Any],
        ui_elements: Dict[str, str]
    ):
        """
        **Property 2: Language Interface Completeness**
        
        For any supported language selection, all user interface elements should be 
        displayed in that language, and switching languages should preserve all session 
        data and user context.
        
        **Validates: Requirements 1.1, 1.5**
        """
        # Skip if no UI elements to test
        assume(len(ui_elements) > 0)
        
        # Create mock interface
        interface = MockLanguageInterface()
        
        # Add UI elements
        for key, text in ui_elements.items():
            interface.add_ui_element(key, text)
        
        # Create and set session
        session = MockUserSession(session_data)
        interface.set_session(session)
        
        # Mock Redis and translation service
        with patch('mandi_platform.translation.service.get_redis_client') as mock_redis_patch:
            mock_redis_patch.return_value = self.get_mock_redis()
            
            # Mock translation service to avoid external API calls
            with patch.object(interface.translation_service, '_translate_with_google') as mock_google:
                with patch.object(interface.translation_service, '_translate_with_inltk') as mock_inltk:
                    # Mock successful translations
                    mock_google.return_value = ("मॉक अनुवाद", 0.9)  # Mock Hindi translation
                    mock_inltk.side_effect = RuntimeError("iNLTK not available")  # Force Google fallback
                    
                    # Perform language switch
                    switch_results = await interface.switch_language(target_language)
                
                # **Property Validation 1: All UI elements should be translated**
                assert switch_results['total_elements'] == len(ui_elements), \
                    f"Expected {len(ui_elements)} elements, got {switch_results['total_elements']}"
                
                # **Property Validation 2: Translation should be attempted for all elements**
                translation_results = switch_results['translation_results']
                assert len(translation_results) == len(ui_elements), \
                    "Translation results should exist for all UI elements"
                
                # **Property Validation 3: Each element should have translation data**
                for element_key in ui_elements.keys():
                    assert element_key in translation_results, \
                        f"Translation result missing for element: {element_key}"
                    
                    result = translation_results[element_key]
                    assert 'original_text' in result, "Original text should be preserved"
                    assert 'translated_text' in result, "Translated text should be provided"
                    assert 'language' in result, "Target language should be recorded"
                    assert result['language'] == target_language, \
                        f"Language mismatch: expected {target_language}, got {result['language']}"
                
                # **Property Validation 4: Session data should be preserved**
                assert switch_results['session_data_preserved'], \
                    "Session data should be preserved during language switch"
                
                # **Property Validation 5: Language preference should be updated**
                current_session = switch_results['current_session_data']
                assert current_session['preferred_language'] == target_language, \
                    f"Session language should be updated to {target_language}"
                
                # **Property Validation 6: Interface language consistency**
                assert interface.validate_language_consistency(), \
                    "All UI elements should be in the same language"
                
                # **Property Validation 7: Interface current language should match target**
                assert interface.current_language == target_language, \
                    f"Interface language should be {target_language}"
    
    @given(
        source_language=supported_languages(),
        target_language=supported_languages(),
        session_data=user_session_data()
    )
    @settings(
        max_examples=50, 
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_language_switch_bidirectional_consistency(
        self,
        source_language: LanguageCode,
        target_language: LanguageCode,
        session_data: Dict[str, Any]
    ):
        """
        Test that language switching is bidirectional and consistent.
        
        Switching from A to B and back to A should preserve all data.
        """
        # Skip if languages are the same
        assume(source_language != target_language)
        
        # Create interface with sample UI elements
        interface = MockLanguageInterface()
        sample_elements = {
            'welcome_message': 'Welcome to Mandi Platform',
            'login_button': 'Login',
            'search_placeholder': 'Search products...',
            'price_label': 'Price',
            'quantity_label': 'Quantity'
        }
        
        for key, text in sample_elements.items():
            interface.add_ui_element(key, text)
        
        # Set initial session with source language
        session_data['preferred_language'] = source_language
        session = MockUserSession(session_data)
        interface.set_session(session)
        
        # Store original state
        original_session_data = session.get_data()
        original_element_texts = interface.get_all_element_texts()
        
        # Mock Redis and translation service
        with patch('mandi_platform.translation.service.get_redis_client') as mock_redis_patch:
            mock_redis_patch.return_value = self.get_mock_redis()
            
            # Mock translation service
            with patch.object(interface.translation_service, '_translate_with_google') as mock_google:
                with patch.object(interface.translation_service, '_translate_with_inltk') as mock_inltk:
                    mock_google.return_value = ("अनुवादित पाठ", 0.9)
                    mock_inltk.side_effect = RuntimeError("iNLTK not available")
                
                    # Switch to target language
                    switch_results_1 = await interface.switch_language(target_language)
                    
                    # Verify first switch
                    assert switch_results_1['session_data_preserved'], \
                        "Session data should be preserved in first switch"
                    assert interface.current_language == target_language, \
                        "Interface should be in target language"
                    
                    # Switch back to source language
                    switch_results_2 = await interface.switch_language(source_language)
                    
                    # **Property Validation: Bidirectional consistency**
                    assert switch_results_2['session_data_preserved'], \
                        "Session data should be preserved in reverse switch"
                    assert interface.current_language == source_language, \
                        "Interface should be back to source language"
                    
                    # Session data should be consistent (excluding language preference)
                    final_session_data = session.get_data()
                    for key, original_value in original_session_data.items():
                        if key != 'preferred_language':
                            assert final_session_data.get(key) == original_value, \
                                f"Session data key '{key}' should be preserved"
                    
                    # Language preference should be updated correctly
                    assert final_session_data['preferred_language'] == source_language, \
                        "Language preference should be back to source language"
    
    @given(
        language=supported_languages(),
        session_data=user_session_data()
    )
    @settings(
        max_examples=50, 
        deadline=8000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_language_switch_with_session_updates(
        self,
        language: LanguageCode,
        session_data: Dict[str, Any]
    ):
        """
        Test that session data updates during language switch are preserved.
        
        If session data is modified during a language switch, those changes
        should be preserved along with the language change.
        """
        # Create interface
        interface = MockLanguageInterface()
        interface.add_ui_element('test_element', 'Test Text')
        
        # Set session
        session = MockUserSession(session_data)
        interface.set_session(session)
        
        # Update session data before language switch
        test_key = 'test_update'
        test_value = 'updated_during_switch'
        session.update_data(test_key, test_value)
        
        # Mock Redis and translation service
        with patch('mandi_platform.translation.service.get_redis_client') as mock_redis_patch:
            mock_redis_patch.return_value = self.get_mock_redis()
            
            # Mock translation service
            with patch.object(interface.translation_service, '_translate_with_google') as mock_google:
                with patch.object(interface.translation_service, '_translate_with_inltk') as mock_inltk:
                    mock_google.return_value = ("परीक्षण पाठ", 0.9)
                    mock_inltk.side_effect = RuntimeError("iNLTK not available")
                    
                    # Perform language switch
                    switch_results = await interface.switch_language(language)
                
                    # **Property Validation: Session updates should be preserved**
                    current_session_data = switch_results['current_session_data']
                    assert current_session_data.get(test_key) == test_value, \
                        "Session data updates should be preserved during language switch"
                    
                    assert current_session_data['preferred_language'] == language, \
                        "Language preference should be updated"
    
    @given(
        language=supported_languages()
    )
    @settings(
        max_examples=30, 
        deadline=8000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_language_switch_error_handling(
        self,
        language: LanguageCode
    ):
        """
        Test that language switching handles translation errors gracefully.
        
        When translation fails, the interface should still switch languages
        but fall back to original text for failed elements.
        """
        # Create interface with elements
        interface = MockLanguageInterface()
        test_elements = {
            'element1': 'First Element',
            'element2': 'Second Element',
            'element3': 'Third Element'
        }
        
        for key, text in test_elements.items():
            interface.add_ui_element(key, text)
        
        # Set session
        session_data = {'user_id': 'test_user', 'preferred_language': LanguageCode.ENGLISH}
        session = MockUserSession(session_data)
        interface.set_session(session)
        
        # Mock Redis and translation service to fail
        with patch('mandi_platform.translation.service.get_redis_client') as mock_redis_patch:
            mock_redis_patch.return_value = self.get_mock_redis()
            
            with patch.object(interface.translation_service, '_translate_with_google') as mock_google:
                with patch.object(interface.translation_service, '_translate_with_inltk') as mock_inltk:
                    # Both engines fail
                    mock_google.side_effect = RuntimeError("Google Translate failed")
                    mock_inltk.side_effect = RuntimeError("iNLTK failed")
                    
                    # Perform language switch
                    switch_results = await interface.switch_language(language)
                
                    # **Property Validation: Graceful error handling**
                    assert switch_results['target_language'] == language, \
                        "Target language should be recorded even with translation errors"
                    
                    # Session should still be updated
                    assert switch_results['session_data_preserved'], \
                        "Session data should be preserved even with translation errors"
                    
                    current_session = switch_results['current_session_data']
                    assert current_session['preferred_language'] == language, \
                        "Language preference should be updated even with translation errors"
                    
                    # Interface language should be updated
                    assert interface.current_language == language, \
                        "Interface language should be updated even with translation errors"
                    
                    # Elements should fall back to original text
                    translation_results = switch_results['translation_results']
                    for key, result in translation_results.items():
                        if not result['success']:
                            assert result['translated_text'] == result['original_text'], \
                                "Failed translations should fall back to original text"
    
    @pytest.mark.asyncio
    async def test_language_interface_with_empty_elements(self):
        """
        Test language interface behavior with no UI elements.
        
        The interface should handle empty element lists gracefully.
        """
        interface = MockLanguageInterface()
        
        # Set session without any UI elements
        session_data = {'user_id': 'test_user', 'preferred_language': LanguageCode.ENGLISH}
        session = MockUserSession(session_data)
        interface.set_session(session)
        
        # Mock Redis
        with patch('mandi_platform.translation.service.get_redis_client') as mock_redis_patch:
            mock_redis_patch.return_value = self.get_mock_redis()
            
            # Switch language with no elements
            switch_results = await interface.switch_language(LanguageCode.HINDI)
        
            # **Property Validation: Empty elements handling**
            assert switch_results['total_elements'] == 0, \
                "Should handle zero UI elements"
            
            assert switch_results['successful_translations'] == 0, \
                "Should have zero successful translations"
            
            assert switch_results['failed_translations'] == 0, \
                "Should have zero failed translations"
            
            assert switch_results['session_data_preserved'], \
                "Session data should be preserved with empty elements"
            
            assert interface.current_language == LanguageCode.HINDI, \
                "Interface language should still be updated"