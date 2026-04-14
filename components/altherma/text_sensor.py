"""Text sensor platform for Altherma Heat Pump.

Provides text sensor entities for reading Altherma heat pump string values
such as operating modes and status messages.
"""
from typing import Dict, Any

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor

from . import CONF_ALTHERMA_ID, ALTHERMA_COMPONENT_SCHEMA

DEPENDENCIES = ["altherma"]

CONF_LABEL = "label"


def validate_label(value: Any) -> str:
    """Validate text sensor label.
    
    Args:
        value: Label value from configuration.
        
    Returns:
        str: Validated label string.
        
    Raises:
        cv.Invalid: If label is empty or invalid.
    """
    value = cv.string(value)
    if not value or not value.strip():
        raise cv.Invalid("Label cannot be empty")
    return value.strip()


CONFIG_SCHEMA = (
    text_sensor.text_sensor_schema()
    .extend(ALTHERMA_COMPONENT_SCHEMA)
    .extend(
        {
            cv.Required(CONF_LABEL): validate_label,
        }
    )
)


async def to_code(config: Dict[str, Any]) -> None:
    """Generate code for Altherma text sensor.
    
    Creates a text sensor entity and registers it with the parent Altherma
    component using the specified label.
    
    Args:
        config: Validated text sensor configuration.
    """
    parent = await cg.get_variable(config[CONF_ALTHERMA_ID])
    label = config[CONF_LABEL]
    
    sens = await text_sensor.new_text_sensor(config)
    cg.add(parent.register_text_sensor(label, sens))
