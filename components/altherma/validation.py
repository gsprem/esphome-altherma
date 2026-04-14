"""Configuration Validation for Altherma Component.

This module handles validation of user-provided configuration including
model names.
"""
from typing import Dict, Any
import os

import esphome.config_validation as cv

# MODELS is loaded lazily to allow definitions to be generated at install time
_MODELS_CACHE = None


def _get_models() -> Dict[str, Any]:
    """Get model definitions, generating them if needed."""
    global _MODELS_CACHE
    if _MODELS_CACHE is None:
        # Ensure definitions are generated before importing
        from .installation import ensure_definitions
        component_dir = os.path.dirname(os.path.abspath(__file__))
        ensure_definitions(component_dir)
        
        from .definitions import MODELS
        _MODELS_CACHE = MODELS
    return _MODELS_CACHE


def validate_model(value: Any) -> str:
    """Validate and normalize model selection.
    
    Args:
        value: Model name from configuration.
        
    Returns:
        str: Validated model name.
        
    Raises:
        cv.Invalid: If model is unknown.
    """
    models = _get_models()
    value = cv.string(value)
    if value not in models:
        available_models = ", ".join(sorted(models.keys())[:10])
        total_models = len(models)
        raise cv.Invalid(
            f"Unknown model '{value}'. "
            f"Available models include: {available_models}... "
            f"({total_models} total models available)"
        )
    return value
