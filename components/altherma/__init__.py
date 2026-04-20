"""ESPHome Altherma Heat Pump Component.

This component integrates Daikin Altherma heat pumps with ESPHome using the
ESPAltherma library for protocol handling and communication.
"""
from typing import Dict, Any, Set
import os

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart
from esphome.const import CONF_ID
from esphome.core import CORE

# Import installation and code generation utilities
from .installation import ensure_espaltherma
from .codegen import generate_labeldefs_from_parameter_ids

# Constants
CONF_ALTHERMA_ID = "altherma_id"

# Default values
DEFAULT_UPDATE_INTERVAL = "30s"

# Component metadata
CODEOWNERS = ["@goran"]
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["sensor", "binary_sensor", "text_sensor", "switch", "select"]
MULTI_CONF = False

# Code generation
altherma_ns = cg.esphome_ns.namespace("altherma")
AlthermaComponent = altherma_ns.class_(
    "AlthermaComponent", cg.PollingComponent, uart.UARTDevice
)


# ==================== Configuration Schema ====================


CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(AlthermaComponent),
        }
    )
    .extend(cv.polling_component_schema(DEFAULT_UPDATE_INTERVAL))
    .extend(uart.UART_DEVICE_SCHEMA)
)

# Schema for child platforms to reference this hub
ALTHERMA_COMPONENT_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ALTHERMA_ID): cv.use_id(AlthermaComponent),
    }
)


# ==================== Main Code Generation ====================


def _collect_platform_parameter_ids() -> Set[str]:
    """Collect all parameter_ids referenced by altherma sensor platforms.
    
    Scans the ESPHome config for sensor, binary_sensor, and text_sensor
    platforms using altherma and extracts their parameter_ids.
    
    Returns:
        Set[str]: Set of parameter_id strings (LabelDef format) used by platforms.
    """
    parameter_ids: Set[str] = set()
    
    platform_types = ["sensor", "binary_sensor", "text_sensor"]
    
    for platform_type in platform_types:
        if platform_type not in CORE.config:
            continue
        
        for entry in CORE.config[platform_type]:
            if not isinstance(entry, dict):
                continue
            if entry.get("platform") != "altherma":
                continue
            if "parameter_id" in entry:
                parameter_ids.add(entry["parameter_id"])
    
    return parameter_ids


async def to_code(config: Dict[str, Any]) -> None:
    """Generate C++ code for the Altherma component.
    
    Validates ESPAltherma availability, configures build flags, and
    generates the labelDefs array from user-specified parameter_ids.
    
    Args:
        config: Validated configuration dictionary.
    """
    # Get component directory for ESPAltherma installation
    component_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure ESPAltherma is available (for converters.h)
    ensure_espaltherma(component_dir)
    
    # Add include path for ESPAltherma headers
    cg.add_build_flag(f"-I{component_dir}")
    
    # Register component
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    
    # Collect parameter_ids from sensor platforms
    platform_parameter_ids = _collect_platform_parameter_ids()
    
    # Generate the labelDefs array from parameter_id strings
    generate_labeldefs_from_parameter_ids(list(platform_parameter_ids))
