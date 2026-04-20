"""Binary sensor platform for Altherma Heat Pump.

Provides binary (on/off) sensor entities for reading Altherma heat pump
boolean status values.
"""
from typing import Dict, Any

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor

from . import CONF_ALTHERMA_ID, ALTHERMA_COMPONENT_SCHEMA
from .validation import validate_parameter_id, parse_labeldef_string, make_sensor_key

DEPENDENCIES = ["altherma"]

CONF_PARAMETER_ID = "parameter_id"


CONFIG_SCHEMA = (
    binary_sensor.binary_sensor_schema()
    .extend(ALTHERMA_COMPONENT_SCHEMA)
    .extend(
        {
            cv.Required(CONF_PARAMETER_ID): validate_parameter_id,
        }
    )
)


async def to_code(config: Dict[str, Any]) -> None:
    """Generate code for Altherma binary sensor.
    
    Creates a binary sensor entity and registers it with the parent Altherma
    component using the specified parameter_id.
    
    Args:
        config: Validated binary sensor configuration.
    """
    parent = await cg.get_variable(config[CONF_ALTHERMA_ID])
    parameter_id = config[CONF_PARAMETER_ID]
    
    # Extract unique key for sensor registration (registry_id_offset)
    parsed = parse_labeldef_string(parameter_id)
    sensor_key = make_sensor_key(parsed)
    
    sens = await binary_sensor.new_binary_sensor(config)
    cg.add(parent.register_binary_sensor(sensor_key, sens))
