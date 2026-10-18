"""
Pluxee Enterprise - AI Controller & Google Genkit SDK Setup (US-INT-10.3)

Configures the official Google Genkit Python SDK client with the Google AI plugin
(googleai/gemini-2.0-flash), ensuring clean lifecycle initialization, environment variable
binding, and error logging.
"""

import logging
import os
from typing import Optional

from config.config_variables import settings

logger = logging.getLogger(__name__)

# Global singleton client instance
_genkit_instance = None


def get_genkit_client():
    """
    Lazily initialize and return the Google Genkit client configured with GoogleAI.
    Uses settings.GENKIT_MODEL (default: googleai/gemini-2.0-flash) and GEMINI_API_KEY.
    """
    global _genkit_instance
    if _genkit_instance is not None:
        return _genkit_instance

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or settings.GEMINI_API_KEY
        or os.getenv("GENKIT_API_KEY")
        or settings.GENKIT_API_KEY
    )
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    try:
        from genkit import Genkit
        from genkit_google_genai import GoogleAI

        model_name = settings.GENKIT_MODEL or "googleai/gemini-2.0-flash"
        _genkit_instance = Genkit(plugins=[GoogleAI()], model=model_name)
        logger.info("Google Genkit SDK initialized successfully with model: %s", model_name)
    except Exception as exc:
        logger.warning(
            "Could not initialize Google Genkit SDK (%s). Heuristic fallback will be used when needed.",
            exc,
        )
        _genkit_instance = None

    return _genkit_instance


def is_genkit_available() -> bool:
    """Check if the Google Genkit client and GEMINI_API_KEY are ready for inference."""
    api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    if not api_key:
        return False
    client = get_genkit_client()
    return client is not None
