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

# Import installation, validation, and code generation utilities
from .installation import ensure_espaltherma
from .validation import validate_model
from .codegen import filter_labels_to_include, generate_labeldefs_code

# Constants
CONF_ALTHERMA_ID = "altherma_id"
CONF_PROTOCOL = "protocol"
CONF_MODEL = "model"

# Default values
DEFAULT_PROTOCOL = "I"
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

AlthermaProtocol = altherma_ns.enum("AlthermaProtocol")
PROTOCOL_OPTIONS = {
    "I": AlthermaProtocol.PROTOCOL_I,
    "S": AlthermaProtocol.PROTOCOL_S,
}


# ==================== Configuration Schema ====================


CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(AlthermaComponent),
            cv.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): cv.enum(
                PROTOCOL_OPTIONS, upper=True
            ),
            cv.Required(CONF_MODEL): validate_model,
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


def _collect_platform_labels() -> Set[str]:
    """Collect all labels referenced by altherma sensor platforms.
    
    Scans the ESPHome config for sensor, binary_sensor, text_sensor,
    switch, and select platforms using altherma and extracts their labels.
    
    Returns:
        Set[str]: Set of label names used by platforms.
    """
    labels: Set[str] = set()
    
    platform_types = ["sensor", "binary_sensor", "text_sensor", "switch", "select"]
    
    for platform_type in platform_types:
        if platform_type not in CORE.config:
            continue
        
        for entry in CORE.config[platform_type]:
            if not isinstance(entry, dict):
                continue
            if entry.get("platform") != "altherma":
                continue
            if "label" in entry:
                labels.add(entry["label"])
    
    return labels


async def to_code(config: Dict[str, Any]) -> None:
    """Generate C++ code for the Altherma component.
    
    Validates ESPAltherma availability, configures build flags, and
    generates the labelDefs array for the selected model.
    
    Args:
        config: Validated configuration dictionary.
    """
    # Get component directory for ESPAltherma installation
    component_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure ESPAltherma and definitions are available
    from .installation import ensure_definitions
    ensure_definitions(component_dir)
    
    from .definitions import MODELS
    
    # Ensure ESPAltherma is available (lazy initialization)
    ensure_espaltherma(component_dir)
    
    # Add include path for ESPAltherma headers
    cg.add_build_flag(f"-I{component_dir}")
    
    # Register component
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    
    # Set protocol
    cg.add(var.set_protocol(config[CONF_PROTOCOL]))
    
    # Load model definitions
    model_name = config[CONF_MODEL]
    model_data = MODELS.get(model_name)
    
    if model_data is None:
        # Should never happen due to validate_model, but defensive check
        raise cv.Invalid(f"Model data not found for '{model_name}'")
    
    # Collect labels from sensor platforms
    platform_labels = _collect_platform_labels()
    
    # Filter labels based on what's used in sensor platforms
    labels_to_include = filter_labels_to_include(
        model_data,
        list(platform_labels),
    )
    
    # Generate the labelDefs array for C++
    generate_labeldefs_code(labels_to_include, model_name)
