"""Select platform for Altherma Heat Pump (Smart Grid mode)."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select
from esphome.const import CONF_ID, CONF_NAME

from . import CONF_ALTHERMA_ID, ALTHERMA_COMPONENT_SCHEMA, altherma_ns

DEPENDENCIES = ["altherma"]

CONF_SG1_PIN = "sg1_pin"
CONF_SG2_PIN = "sg2_pin"

AlthermaSelect = altherma_ns.class_("AlthermaSelect", select.Select, cg.Component)

# Smart Grid modes
SMART_GRID_OPTIONS = [
    "Normal",       # 0: SG1=open, SG2=open
    "Forced OFF",   # 1: SG1=open, SG2=close
    "Recommended ON",  # 2: SG1=close, SG2=open
    "Forced ON",    # 3: SG1=close, SG2=close
]

CONFIG_SCHEMA = (
    select.select_schema(AlthermaSelect)
    .extend(
        {
            cv.Required(CONF_SG1_PIN): cv.int_,
            cv.Required(CONF_SG2_PIN): cv.int_,
        }
    )
    .extend(ALTHERMA_COMPONENT_SCHEMA)
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    """Generate code for Altherma Smart Grid select."""
    var = await select.new_select(config, options=SMART_GRID_OPTIONS)
    await cg.register_component(var, config)
    
    cg.add(var.set_sg1_pin(config[CONF_SG1_PIN]))
    cg.add(var.set_sg2_pin(config[CONF_SG2_PIN]))
