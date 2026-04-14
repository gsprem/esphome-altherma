# ESPHome Altherma Component

An ESPHome external component for monitoring and controlling Daikin Altherma, ROTEX, and HOVAL Belaria heat pumps.
This component is based on the [ESPAltherma](https://github.com/raomin/ESPAltherma) project, adapted for native ESPHome integration.


## Quick Setup

1. **Add the component to your ESPHome configuration:**

```yaml
external_components:
  - source: github://gsprem/esphome-altherma@main
    components: [altherma]
    refresh: 1d

uart:
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 9600
  parity: EVEN

altherma:
  id: heatpump
  protocol: I 
  model: "ALTHERMA(HYBRID)"
  update_interval: 30s

sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Outdoor air temp."
    name: "Outdoor Temperature"
    
  - platform: altherma
    altherma_id: heatpump
    label: "DHW tank temp. (R5T)"
    name: "DHW Tank Temperature"
```

2. **Wire your ESP32 to the heat pump's X10A port**
3. **Flash and enjoy!**

## Hardware Requirements

- ESP32 or ESP8266 board
- 5-pin JST EH 2.5mm connector (or Dupont wires)
- Connection to heat pump X10A port

### Wiring

| X10A Pin | ESP32 |
|----------|-------|
| 1 - 5V   | VIN (optional power) |
| 2 - TX   | RX_PIN (GPIO16) |
| 3 - RX   | TX_PIN (GPIO17) |
| 4 - NC   | Not connected |
| 5 - GND  | GND |

## Installation

### Add External Component

```yaml
external_components:
  - source: https://github.com/gsprem/esphome-altherma
    components: [altherma]
```

### Configure UART

```yaml
uart:
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 9600
  parity: EVEN
```

### 3. Add Altherma Hub

```yaml
altherma:
  id: heatpump
  protocol: I        # Use 'S' for older ROTEX models
  model: "ALTHERMA(HYBRID)"
  update_interval: 30s
```

### 4. Add Sensors

```yaml
sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Outdoor air temp."
    name: "Outdoor Temperature"
    
  - platform: altherma
    altherma_id: heatpump
    label: "DHW tank temp. (R5T)"
    name: "DHW Tank Temperature"

text_sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Operation Mode"
    name: "Operation Mode"
```

## Available Models

The `model` parameter must match your heat pump exactly. Find your model in the Daikin indoor unit label (e.g., ERGA04DV, EPRA14DV).

### Protocol I Models (Newer Daikin)

**Standard Models:**
```
ALTHERMA(HYBRID)
ALTHERMA(LT_CA_CB_04-08KW)
ALTHERMA(LT_CA_CB_11-16KW)
ALTHERMA(LT_MULTI_DHWHP)
ALTHERMA(LT_MULTI_HYBRID)
Altherma(EBLA-EDLA D series 4-8kW Monobloc)
Altherma(EBLA-EDLA D series 9-16kW Monobloc)
Altherma(EGSAH-X-EWSAH-X-D series 6-10kW GEO3)
Altherma(EGSQH-A series 10kW GEO2)
Altherma(EPGA D EAB-EAV-EAVZ D(J) series 11-16kW)
Altherma(EPRA D ETSH-X 16P30-50 D series 14-16kW-ECH2O)
Altherma(EPRA D ETV16-ETB16-ETVZ16 D series 14-16kW)
Altherma(EPRA D_D7 ETSH-X 16P30-50 E_E7 series 14-18kW-ECH2O)
Altherma(EPRA D_D7 ETV16-ETB16-ETVZ16 E_E7 series 14-18kW)
Altherma(EPRA E ETSH-X 16P30-50 E series 8-12kW-ECH2O)
Altherma(EPRA E ETV16-ETB16-ETVZ16 E_EJ series 8-12kW)
Altherma(ERGA D EHSH-X P30-50 D series 04-08kW-ECH2O)
Altherma(ERGA D EHV-EHB-EHVZ DA series 04-08kW)
Altherma(ERGA D EHV-EHB-EHVZ DJ series 04-08 kW)
Altherma(ERGA E EHSH-X P30-50 E_EF series 04-08kW-ECH2O)
Altherma(ERGA E EHV-EHB-EHVZ E_EJ series 04-08kW)
Altherma(ERLA D EBSH-X 16P30-50 D SERIES 11-16kW-ECH2O)
Altherma(ERLA D EBV-EBB-EBVZ D SERIES 11-16kW)
Altherma(ERLA03 D EHFH-EHFZ DJ series 3kW)
Altherma(LT_CB_04-08kW Bizone)
Altherma(LT_CB_11-16kW Bizone)
Altherma(LT_EBLQ-EBLQ-CA series 5-7kW Monobloc)
Altherma(LT_EBLQ-EDLQ-CA series 11-16kW Monobloc)
Daikin Mini chiller(EWAA-EWYA D series 4-8kW)
Daikin Mini chiller(EWAA-EWYA D series 9-16kW)
Daikin Mini chiller(EWAQ-EWYQ B series 4-8kW)
DEFAULT
EKHWET-BAV3(MULTI DHW TANK)
```

### Protocol S Models (Older ROTEX/Daikin)

```
PROTOCOL_S
PROTOCOL_S_ROTEX
```

### Localized Models

Prefix with `French/`, `German/`, or `Spanish/` for localized sensor labels:
```
French/ALTHERMA(HYBRID)
French/ALTHERMA(LT_CA_CB_04-08KW)
German/ALTHERMA(HYBRID)
German/ALTHERMA(LT_CA_CB_04-08KW)
Spanish/ALTHERMA(HYBRID)
Spanish/ALTHERMA(LT_CA_CB_04-08KW)
... (all standard models available with each prefix)
```

### Finding Your Model

1. Check the indoor unit label for model code (e.g., ERGA04DV)
2. Match the prefix: ERGA, EPRA, EBLA, EDLA, EBLQ, etc.
3. Match the power rating: 04=4kW, 08=8kW, 14=14kW, etc.
4. Match the series letter: D, E, etc.

If unsure, start with `DEFAULT` and check logs for registry responses.

## Building and Flashing

### First-time Build

```bash
# Validate configuration
esphome config your-config.yaml

# Compile firmware
esphome compile your-config.yaml
```

### Docker

If using ESPHome in Docker:

```bash
docker run --rm -v "${PWD}":/config -it ghcr.io/esphome/esphome compile your-config.yaml
```

### Build Requirements

- ESPHome 2021.8.0 or later (latest stable recommended)

## Finding Available Labels

Labels are defined in ESPAltherma model definition files. To find available labels for your model:

1. Go to [ESPAltherma definition files](https://github.com/raomin/ESPAltherma/tree/main/include/def)
2. Find your model's `.h` file (e.g., `ALTHERMA(HYBRID).h`)
3. Each line like `{0x60, 2, 315, 1, -1, "Outdoor air temp."}` defines a label
4. The last quoted string (e.g., `"Outdoor air temp."`) is the label name
5. Use these exact label names in the sensor `label:` field

**Example from model file:**
```c
{0x60, 0, 304, 2, -1, "Leaving water temp. before BUH (R1T)"},
{0x60, 2, 315, 1, -1, "Outdoor air temp."},
{0x60, 5, 316, 2, -1, "DHW tank temp. (R5T)"},
```

**Usage:**
```yaml
sensor:
  - platform: altherma
    label: "Outdoor air temp."  # Must match exactly from model file
    name: "Outdoor Temperature"
```

Common labels include:

### Temperatures
- `Outdoor air temp.`
- `DHW tank temp. (R5T)`
- `Leaving water temp. before BUH (R1T)`
- `Inlet water temp.(R4T)`
- `Discharge pipe temp.`
- `Suction pipe temp.`

### Electrical
- `INV primary current (A)`
- `Voltage (V)`

### Status
- `Operation Mode`
- `I/U operation mode`
- `Error type`
- `Error Code`
- `Thermostat ON/OFF`

### Flow
- `Flow sensor (l/min)`

## Optional: Thermostat Relay

Control your heat pump's external thermostat input:

```yaml
switch:
  - platform: altherma
    altherma_id: heatpump
    pin: 25
    name: "Heating Control"
```

## Optional: Smart Grid

Control Smart Grid modes via SG1/SG2 relays:

```yaml
select:
  - platform: altherma
    altherma_id: heatpump
    sg1_pin: 26
    sg2_pin: 27
    name: "Smart Grid Mode"
```

Modes:
| Mode | SG1 | SG2 | Effect |
|------|-----|-----|--------|
| Normal | open | open | Normal operation |
| Forced OFF | open | close | HP forced OFF |
| Recommended ON | close | open | +5°C setpoint |
| Forced ON | close | close | DHW to 70°C |

### Updating ESPAltherma Version

The component pins ESPAltherma to commit `281033c8` for stability. To update:

1. Find the new commit SHA from [ESPAltherma releases](https://github.com/raomin/ESPAltherma)
2. Update `ESPALTHERMA_COMMIT` in `components/altherma/__init__.py`
3. Re-run the sync script to update model definitions

## Troubleshooting

### Validation error: "Unknown model"
- Model name must match exactly (case-sensitive)
- Check the Available Models section above
- Use `DEFAULT` to test basic connectivity

### Validation error: "Unknown label"
- Sensor label must match exactly as defined in the model
- Labels are case-sensitive and include punctuation
- Check logs for available labels in your model

### No sensor data after compile
- Verify UART TX/RX pin assignment matches wiring
- Check that `parity: EVEN` is set in UART config
- Ensure heat pump is powered on
- Try `update_interval: 10s` for faster debugging

### Timeout errors in logs
- Check wiring, especially GND connection
- Verify RX/TX pins are not swapped
- Try different GPIO pins (avoid strapping pins)

### CRC errors in logs
- Usually a wiring issue
- Use shorter cables or shielded wires
- Check for loose connections

### 0x15 0xEA errors in logs
- Heat pump uses Protocol S (older models)
- Change `protocol: S` in your YAML
- Use a `PROTOCOL_S` model definition

### Some sensors always empty
- Not all labels exist on all heat pump models
- The label may be commented out (disabled) in the model definition
- Check the model's `.h` file in ESPAltherma to verify the label exists

## License

MIT License - see [LICENSE](LICENSE)
