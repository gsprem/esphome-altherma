"""C++ Code Generation for Altherma Component.

This module handles generating C++ labelDefs arrays and related code
for the ESPHome Altherma component.
"""
from typing import Dict, List, Any
import logging

import esphome.codegen as cg

_LOGGER = logging.getLogger(__name__)


def _escape_cpp_string(value: str) -> str:
    """Escape a string for safe use in C++ code.
    
    Args:
        value: String to escape.
        
    Returns:
        str: Escaped string safe for C++ string literals.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _generate_label_entry(label_def: Dict[str, Any]) -> str:
    """Generate a C++ LabelDef initializer entry.
    
    Args:
        label_def: Label definition dictionary.
        
    Returns:
        str: C++ initializer string.
    """
    label_str = _escape_cpp_string(label_def["label"])
    return (
        f'{{{label_def["registry_id"]}, '
        f'{label_def["offset"]}, '
        f'{label_def["conv_id"]}, '
        f'{label_def["data_size"]}, '
        f'{label_def["data_type"]}, '
        f'"{label_str}"}}'
    )


def filter_labels_to_include(
    model_data: Dict[str, Any],
    explicit_labels: List[str],
) -> List[Dict[str, Any]]:
    """Filter label definitions to only include user-specified labels.
    
    Args:
        model_data: Model definition data.
        explicit_labels: List of label names to include.
        
    Returns:
        List[Dict[str, Any]]: Filtered list of label definitions.
    """
    return [
        label_def
        for label_def in model_data["labels"]
        if label_def["label"] in explicit_labels
    ]


def generate_labeldefs_code(
    labels_to_include: List[Dict[str, Any]],
    model_name: str,
) -> None:
    """Generate C++ labelDefs array code.
    
    Generates global C++ declarations for the labelDefs array and its size.
    If no labels are provided, generates an empty array with appropriate
    warning logging.
    
    Args:
        labels_to_include: List of label definitions to generate code for.
        model_name: Model name for logging purposes.
    """
    if labels_to_include:
        label_entries = [
            _generate_label_entry(label_def)
            for label_def in labels_to_include
        ]
        array_init = ",\n  ".join(label_entries)
        
        cg.add_global(
            cg.RawExpression(f"LabelDef labelDefs[] = {{\n  {array_init}\n}}")
        )
        cg.add_global(
            cg.RawExpression(f"const size_t labelDefs_size = {len(label_entries)}")
        )
        
        _LOGGER.info(
            "Generated %d label definitions for model '%s':",
            len(label_entries),
            model_name,
        )
        for label_def in labels_to_include:
            _LOGGER.info("  - %s", label_def["label"])
    else:
        # Empty array fallback
        cg.add_global(cg.RawExpression("LabelDef labelDefs[] = {}"))
        cg.add_global(cg.RawExpression("const size_t labelDefs_size = 0"))
        
        _LOGGER.warning(
            "No labels configured for model '%s'. Component will not expose data.",
            model_name,
        )
