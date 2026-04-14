"""Switch platform for Altherma Heat Pump (thermostat relay)."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch, output
from esphome.const import CONF_ID, CONF_NAME, CONF_PIN

from . import CONF_ALTHERMA_ID, ALTHERMA_COMPONENT_SCHEMA, altherma_ns

DEPENDENCIES = ["altherma"]

AlthermaSwitch = altherma_ns.class_("AlthermaSwitch", switch.Switch, cg.Component)

CONFIG_SCHEMA = (
    switch.switch_schema(AlthermaSwitch)
    .extend(
        {
            cv.Required(CONF_PIN): cv.int_,
        }
    )
    .extend(ALTHERMA_COMPONENT_SCHEMA)
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    """Generate code for Altherma switch."""
    var = await switch.new_switch(config)
    await cg.register_component(var, config)
    
    cg.add(var.set_pin(config[CONF_PIN]))
