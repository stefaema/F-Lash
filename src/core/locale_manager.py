# core/locale_manager.py

import json
from typing import Dict, Any, List
import importlib.resources as pkg_resources
from nicegui import app
from core.log_manager import logger

# The reference to the directory where locale files (e.g., en.json) are stored.
I18N_PACKAGE_REF = pkg_resources.files('i18n')

FALLBACK_LOCALE = 'en'

class LocaleManager:
    """
    Manages locale settings and provides robust translation services for NiceGUI.
    It loads all supported locales dynamically and links the active locale state 
    to the NiceGUI user session ('ui_language').
    """
    
    def __init__(self):
        """Initializes the manager, dynamically loading all supported locale files."""
        self._fallback_translations: Dict[str, str] = {}
        self._all_translations: Dict[str, Dict[str, str]] = {}
        
        # 1. Load fallback first for guaranteed coverage
        self._fallback_translations = self._load_translations(FALLBACK_LOCALE)
        self._all_translations[FALLBACK_LOCALE] = self._fallback_translations

        # 2. Dynamic Locale Discovery (The Fix)
        if I18N_PACKAGE_REF is None:
            logger.error("I18N package reference is invalid. Cannot discover locales.")
            return

        try:
            for path in I18N_PACKAGE_REF.iterdir():
                if path.name.endswith('.json'):
                    locale_code = path.stem # 'path.stem' gives 'en' from 'en.json'
                    
                    # Load the discovered locale unless it's the fallback we already loaded
                    if locale_code not in self._all_translations:
                        self._all_translations[locale_code] = self._load_translations(locale_code)
                        
        except Exception as e:
            logger.error(f"Error during dynamic locale discovery: {e}")
        
        logger.info(f"LocaleManager initialized. Dynamically Supported: {list(self._all_translations.keys())}. Fallback: {FALLBACK_LOCALE}")

    def _load_translations(self, locale: str) -> Dict[str, str]:
        """
        Loads translations for a specific locale from a JSON file using 
        importlib.resources for robust path handling.
        """
        if I18N_PACKAGE_REF is None:
            return {}
        
        file_name = f'{locale}.json'
        
        try:
            # 1. Access the resource file within the package
            file_path = I18N_PACKAGE_REF / file_name
            
            # 2. Open and read the content stream
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise TypeError("Translation file root must be a dictionary.")
                logger.info(f"Loaded translations for locale '{locale}'.")
                return data
        except FileNotFoundError:
            logger.warning(f"Translation resource not found for locale '{locale}' ({file_name}).")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in file for locale '{locale}': {e}")
            return {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading locale '{locale}': {e}")
            return {}

    @property
    def supported_locales(self) -> List[str]:
        """Returns a list of all dynamically supported locale codes."""
        return list(self._all_translations.keys())

    def T(self, key: str, use_fallback=False, **kwargs: Any) -> str:
        """
        The core translation function, retrieving the locale from the NiceGUI user session.
        
        Args:
            key: The identifier key for the string to translate.
            **kwargs: Variables for string interpolation.
        
        Returns:
            The translated string, or a fallback message if the key is missing.
        """
        # 1. Determine current locale from NiceGUI session
        # Use FALLBACK_LOCALE if user storage is not yet populated (pre-login)
        if use_fallback:
            current_locale = FALLBACK_LOCALE
        else:
            current_locale = app.storage.user.get('ui_language', FALLBACK_LOCALE)
        
        # 2. Get translation dictionary for the current locale
        translations = self._all_translations.get(current_locale, {})

        # 3. Look up in current locale
        translated_string = translations.get(key)
        
        # 4. Look up in fallback locale if key is missing
        if translated_string is None:
            logger.warning(f"Missing translation key '{key}'.")
            translated_string = self._fallback_translations.get(key)
            if translated_string is None:
                # 5. Last resort: Return the key itself
                logger.warning(f"Missing translation key '{key}' in both current and fallback locales.")
                return f"!! {key} !!"

        # 6. Perform string formatting
        if kwargs:
            try:
                # Use .format() for interpolation
                return translated_string.format(**kwargs)
            except Exception as e:
                logger.error(f"Formatting failed for key '{key}' in locale '{current_locale}': {e}")
                return translated_string

        return translated_string

# Create a globally accessible singleton instance
global_locale_manager = LocaleManager()

# Define the short alias for translation for ease of use in UI files
T = global_locale_manager.T

# Provide access to the full list of supported locales
SUPPORTED_LOCALES = global_locale_manager.supported_locales
