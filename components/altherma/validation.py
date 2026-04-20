"""Configuration Validation for Altherma Component.

This module handles validation of user-provided configuration including
parameter_id LabelDef specifications with security checks to prevent code injection.
"""
from typing import Dict, Any, Optional, Tuple
import re

import esphome.config_validation as cv


# ==================== LabelDef Parsing & Validation ====================

# Allowed characters in label string - alphanumeric, spaces, and common punctuation
# Explicitly EXCLUDES: " \ { } ; to prevent C++ code injection
LABEL_ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9 _.()/<>:=%+-]+$')

# Maximum lengths for safety
MAX_LABEL_LENGTH = 100
MAX_PARAMETER_ID_LENGTH = 150


def parse_labeldef_string(value: str) -> Optional[Dict[str, Any]]:
    """Parse a LabelDef string into its components with security validation.
    
    Accepts format: {0x60,3,204,1,-1,"Error Code"}
    
    Security: Validates all fields to prevent C++ code injection:
    - Registry ID: hex (0x00-0xFF) or decimal (0-255)
    - Offset: non-negative integer (0-255)
    - Conv ID: non-negative integer (0-999)
    - Data size: positive integer (1-8)
    - Data type: integer (-9 to 99, typically -1, 0, 1, 2)
    - Label: alphanumeric with limited punctuation, no quotes/backslashes/braces
    
    Args:
        value: LabelDef string from YAML configuration.
        
    Returns:
        Dict with keys: registry_id, offset, conv_id, data_size, data_type, label
        Returns None if parsing fails.
    """
    if value is None or not isinstance(value, str):
        return None
    
    if not value or len(value) > MAX_PARAMETER_ID_LENGTH:
        return None
    
    # Pattern matches: {registryID, offset, convID, dataSize, dataType, "label"}
    # Strict pattern to prevent injection
    # dataType allows -9 to 99 (ESPAltherma uses -1, 0, 1, 2, etc.)
    pattern = r'^\s*\{\s*(0x[0-9a-fA-F]{1,2}|[0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9])\s*,\s*(-?[0-9]{1,2})\s*,\s*"([^"\\{};]+)"\s*\}\s*$'
    
    match = re.match(pattern, value)
    if not match:
        return None
    
    # Parse and validate registry_id (0x00-0xFF or 0-255)
    registry_str = match.group(1)
    if registry_str.lower().startswith('0x'):
        registry_id = int(registry_str, 16)
    else:
        registry_id = int(registry_str)
    
    if not (0 <= registry_id <= 255):
        return None
    
    # Parse and validate offset (0-255)
    offset = int(match.group(2))
    if not (0 <= offset <= 255):
        return None
    
    # Parse and validate conv_id (0-999, converter function index)
    conv_id = int(match.group(3))
    if not (0 <= conv_id <= 999):
        return None
    
    # Parse and validate data_size (1-8 bytes)
    data_size = int(match.group(4))
    if not (1 <= data_size <= 8):
        return None
    
    # Parse data_type (-1, 0, or 1) - already validated by regex
    data_type = int(match.group(5))
    
    # Validate label string
    label = match.group(6)
    if not label or len(label) > MAX_LABEL_LENGTH:
        return None
    
    if not LABEL_ALLOWED_CHARS.match(label):
        return None
    
    return {
        "registry_id": registry_id,
        "offset": offset,
        "conv_id": conv_id,
        "data_size": data_size,
        "data_type": data_type,
        "label": label,
    }


def validate_parameter_id(value: Any) -> str:
    """Validate parameter_id LabelDef format with security checks.
    
    Expects format: {0x60,3,204,1,-1,"Error Code"}
    This format matches ESPAltherma definition files for easy copy-paste.
    
    Security: All fields are strictly validated to prevent C++ code injection
    when generating the labelDefs array.
    
    Args:
        value: Parameter ID value from configuration (LabelDef string).
        
    Returns:
        str: Validated and normalized parameter_id string.
        
    Raises:
        cv.Invalid: If parameter_id format is invalid or contains unsafe characters.
    """
    value = cv.string(value)
    if not value or not value.strip():
        raise cv.Invalid("parameter_id cannot be empty")
    
    value = value.strip()
    
    if len(value) > MAX_PARAMETER_ID_LENGTH:
        raise cv.Invalid(
            f"parameter_id too long (max {MAX_PARAMETER_ID_LENGTH} characters)"
        )
    
    parsed = parse_labeldef_string(value)
    
    if parsed is None:
        raise cv.Invalid(
            f"Invalid parameter_id format: '{value}'\n"
            f'Expected format: {{0xRR,offset,convID,size,type,"Label"}}\n'
            f'Example: {{0x60,2,315,1,-1,"Outdoor air temp."}}\n'
            f"Copy the complete LabelDef line from your model's .h file in ESPAltherma.\n"
            f"Note: Label may only contain letters, numbers, spaces, and: _ . ( ) / < > : = % + -"
        )
    
    return value


def get_labeldef_key(parsed: Dict[str, Any]) -> Tuple[int, int]:
    """Get unique key for a parsed LabelDef.
    
    Uses (registry_id, offset) as unique identifier since no two parameters
    can exist at the same memory location.
    
    Args:
        parsed: Parsed LabelDef dictionary.
        
    Returns:
        Tuple[int, int]: (registry_id, offset) unique key.
    """
    return (parsed["registry_id"], parsed["offset"])


def make_sensor_key(parsed: Dict[str, Any]) -> str:
    """Generate unique sensor registration key from parsed LabelDef.
    
    Uses registry_id and offset as the key since these uniquely identify
    a parameter in the heat pump's register space. This avoids collisions
    with duplicate labels (e.g., 'Error Code' exists at multiple locations).
    
    Args:
        parsed: Parsed LabelDef dictionary from parse_labeldef_string().
        
    Returns:
        str: Unique key in format "registryID_offset" (e.g., "96_2").
    """
    return f"{parsed['registry_id']}_{parsed['offset']}"


def escape_label_for_cpp(label: str) -> str:
    """Escape a label string for safe use in C++ code.
    
    Since we've already validated the label contains only safe characters,
    this is mainly for defense-in-depth.
    
    Args:
        label: Pre-validated label string.
        
    Returns:
        str: Escaped string safe for C++ string literals.
    """
    # Double-escape backslashes and quotes (should not exist due to validation)
    result = label.replace("\\", "\\\\").replace('"', '\\"')
    return result
