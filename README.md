# ESPHome Altherma Component

An ESPHome external component for monitoring and controlling Daikin Altherma, ROTEX, and HOVAL Belaria heat pumps.
This component is based on the [ESPAltherma](https://github.com/raomin/ESPAltherma) project, adapted for native ESPHome integration.

## Quick Start

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

text_sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Operation Mode"
    name: "Operation Mode"

binary_sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Thermostat ON/OFF"
    name: "Thermostat Active"
```

---

# Configuration

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

## External Component

```yaml
external_components:
  - source: https://github.com/gsprem/esphome-altherma
    components: [altherma]
    refresh: 1d  # Check for updates daily (use "0s" for always latest)
```

## Altherma Hub

```yaml
altherma:
  id: heatpump
  protocol: I        # Use 'S' for older ROTEX models
  model: "ALTHERMA(HYBRID)"
  update_interval: 30s
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | Yes | Unique identifier for the hub |
| `protocol` | Yes | `I` for newer Daikin, `S` for older ROTEX |
| `model` | Yes | Heat pump model (see Available Models) |
| `update_interval` | No | Polling interval (default: 30s) |

## Available Models

The `model` parameter must match your heat pump exactly. Find your model on the indoor unit label (e.g., ERGA04DV, EPRA14DV).

### Protocol I Models (Newer Daikin)

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

### Localized Models

Prefix with `French/`, `German/`, or `Spanish/` for localized sensor labels:

```
French/ALTHERMA(HYBRID)
German/ALTHERMA(HYBRID)
Spanish/ALTHERMA(HYBRID)
... (all standard models available with each prefix)
```

### Finding Your Model

1. Check the indoor unit label for model code (e.g., ERGA04DV)
2. Match the prefix: ERGA, EPRA, EBLA, EDLA, EBLQ, etc.
3. Match the power rating: 04=4kW, 08=8kW, 14=14kW, etc.
4. Match the series letter: D, E, etc.

If unsure, start with `DEFAULT` and check logs for registry responses.

## Sensors and Labels

### Finding Available Labels

Labels are defined in ESPAltherma model definition files:

1. Go to [ESPAltherma definition files](https://github.com/raomin/ESPAltherma/tree/main/include/def)
2. Find your model's `.h` file (e.g., `ALTHERMA(HYBRID).h`)
3. Each line defines a label with this format:
   ```c
   {registryID, offset, converterID, dataSize, dataType, "Label Name"}
   ```
4. The last quoted string is the label name to use in your config

**Example from model file:**
```c
{0x60, 0, 304, 2, -1, "Leaving water temp. before BUH (R1T)"},
{0x60, 2, 315, 1, -1, "Outdoor air temp."},
{0x62, 1, 152, 1, -1, "Operation Mode"},
{0x20, 4, 307, 1,  0, "Thermostat ON/OFF"},
```

### Choosing Sensor Type

The **`dataType`** field (5th value) tells you which ESPHome platform to use:

| dataType | ESPHome Platform | Description |
|----------|------------------|-------------|
| `-1` | `sensor` or `text_sensor` | See converterID below |
| `0` | `binary_sensor` | ON/OFF boolean value |
| `1` | `text_sensor` | String/text value |

When `dataType` is `-1`, check the **`converterID`** (3rd value) or **label name**:

| Indicator | ESPHome Platform | Examples |
|-----------|------------------|----------|
| Label has units: `(°C)`, `(A)`, `(V)`, `(l/min)`, `(kW)`, `(%)` | `sensor` | "Outdoor air temp.", "Voltage (V)" |
| Label ends with `temp.` or `temp` | `sensor` | "DHW tank temp. (R5T)" |
| Label contains "Mode", "type", "Code", "status" | `text_sensor` | "Operation Mode", "Error Code" |
| Label contains "ON/OFF" | `binary_sensor` | "Thermostat ON/OFF" |

**Quick rule:** If it's a number with units → `sensor`. If it's a state/mode → `text_sensor`. If it's ON/OFF → `binary_sensor`.

### Numeric Sensors

Use `sensor` for temperatures, currents, voltages, flow rates, and other numeric values:

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
    
  - platform: altherma
    altherma_id: heatpump
    label: "INV primary current (A)"
    name: "Inverter Current"
    
  - platform: altherma
    altherma_id: heatpump
    label: "Flow sensor (l/min)"
    name: "Water Flow"
```

Common numeric labels:
- `Outdoor air temp.`
- `DHW tank temp. (R5T)`
- `Leaving water temp. before BUH (R1T)`
- `Inlet water temp.(R4T)`
- `Discharge pipe temp.`
- `INV primary current (A)`
- `Voltage (V)`
- `Flow sensor (l/min)`

### Text Sensors

Use `text_sensor` for modes, status strings, and error codes:

```yaml
text_sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Operation Mode"
    name: "Operation Mode"
    
  - platform: altherma
    altherma_id: heatpump
    label: "I/U operation mode"
    name: "Indoor Unit Mode"
    
  - platform: altherma
    altherma_id: heatpump
    label: "Error Code"
    name: "Error Code"
```

Common text labels:
- `Operation Mode`
- `I/U operation mode`
- `Error type`
- `Error Code`

### Binary Sensors

Use `binary_sensor` for ON/OFF states:

```yaml
binary_sensor:
  - platform: altherma
    altherma_id: heatpump
    label: "Thermostat ON/OFF"
    name: "Thermostat Active"
```

Common binary labels:
- `Thermostat ON/OFF`
- `Defrost Operation`
- `DHW Reheat`

## Optional: Thermostat Relay

Control your heat pump's external thermostat input via GPIO:

```yaml
switch:
  - platform: altherma
    altherma_id: heatpump
    pin: 25
    name: "Heating Control"
```

## Optional: Smart Grid

Control Smart Grid modes via SG1/SG2 relay outputs:

```yaml
select:
  - platform: altherma
    altherma_id: heatpump
    sg1_pin: 26
    sg2_pin: 27
    name: "Smart Grid Mode"
```

| Mode | SG1 | SG2 | Effect |
|------|-----|-----|--------|
| Normal | open | open | Normal operation |
| Forced OFF | open | close | HP forced OFF |
| Recommended ON | close | open | +5°C setpoint |
| Forced ON | close | close | DHW to 70°C |

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

---

# Development

## Building and Flashing

### Validate and Compile

```bash
# Validate configuration
esphome config your-config.yaml

# Compile firmware
esphome compile your-config.yaml

# Upload to device
esphome upload your-config.yaml
```

### Using Docker

```bash
docker run --rm -v "${PWD}":/config -it ghcr.io/esphome/esphome compile your-config.yaml
```

### Requirements

- ESPHome 2021.8.0 or later (latest stable recommended)

## Updating ESPAltherma Version

The component pins ESPAltherma to a specific commit for stability. To update:

1. Find the new commit SHA from [ESPAltherma commits](https://github.com/raomin/ESPAltherma/commits/main)
2. Update `ESPALTHERMA_COMMIT_HASH` in `components/altherma/installation.py`
3. Delete the cached ESPAltherma directory to force re-clone

## License

MIT License - see [LICENSE](LICENSE)
