"""C++ Code Generation for Altherma Component.

This module handles generating C++ labelDefs arrays from user-specified
parameter_id LabelDef strings.
"""
from typing import Dict, List, Any
import logging

import esphome.codegen as cg

from .validation import parse_labeldef_string, escape_label_for_cpp

_LOGGER = logging.getLogger(__name__)


def _generate_label_entry(parsed: Dict[str, Any]) -> str:
    """Generate a C++ LabelDef initializer entry.
    
    Args:
        parsed: Parsed LabelDef dictionary from parse_labeldef_string().
        
    Returns:
        str: C++ initializer string for LabelDef struct.
    """
    label_str = escape_label_for_cpp(parsed["label"])
    return (
        f'{{{parsed["registry_id"]}, '
        f'{parsed["offset"]}, '
        f'{parsed["conv_id"]}, '
        f'{parsed["data_size"]}, '
        f'{parsed["data_type"]}, '
        f'"{label_str}"}}'
    )


def generate_labeldefs_from_parameter_ids(parameter_id_strings: List[str]) -> None:
    """Generate C++ labelDefs array from parameter_id strings.
    
    Parses each parameter_id string (LabelDef format) and generates
    the corresponding C++ labelDefs array.
    
    Args:
        parameter_id_strings: List of LabelDef strings from YAML config.
    """
    if not parameter_id_strings:
        # Empty array fallback
        cg.add_global(cg.RawExpression("LabelDef labelDefs[] = {}"))
        cg.add_global(cg.RawExpression("const size_t labelDefs_size = 0"))
        _LOGGER.warning("No parameter_ids configured. Component will not expose data.")
        return
    
    # Parse all parameter_id strings
    parsed_defs = []
    for param_str in parameter_id_strings:
        parsed = parse_labeldef_string(param_str)
        if parsed is not None:
            parsed_defs.append(parsed)
        else:
            # Should not happen if validation passed, but log just in case
            _LOGGER.error("Failed to parse parameter_id: %s", param_str)
    
    if not parsed_defs:
        cg.add_global(cg.RawExpression("LabelDef labelDefs[] = {}"))
        cg.add_global(cg.RawExpression("const size_t labelDefs_size = 0"))
        _LOGGER.warning("No valid parameter_ids after parsing.")
        return
    
    # Generate C++ entries
    label_entries = [_generate_label_entry(parsed) for parsed in parsed_defs]
    array_init = ",\n  ".join(label_entries)
    
    cg.add_global(
        cg.RawExpression(f"LabelDef labelDefs[] = {{\n  {array_init}\n}}")
    )
    cg.add_global(
        cg.RawExpression(f"const size_t labelDefs_size = {len(label_entries)}")
    )
    
    _LOGGER.info("Generated %d parameter definitions:", len(label_entries))
    for parsed in parsed_defs:
        _LOGGER.info("  - %s (registry 0x%02X, offset %d)", 
                     parsed["label"], parsed["registry_id"], parsed["offset"])
