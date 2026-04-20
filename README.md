# ESPHome Altherma Component

An ESPHome external component for monitoring Daikin Altherma heat pumps.
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
  update_interval: 30s

sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x20,0,105,2,1,"R1T-Outdoor air temp."}'
    accuracy_decimals: 1
    unit_of_measurement: "°C"
    device_class: "temperature"
    name: "Outdoor Temperature"

  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x62,11,105,1,2,"Water pressure"}'
    accuracy_decimals: 1
    device_class: "pressure"
    unit_of_measurement: "bar"
    name: "Water pressure (bar)"

text_sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x10,0,217,1,-1,"Operation Mode"}'
    name: "Operation Mode"
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
  update_interval: 30s
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | Yes | Unique identifier for the hub |
| `update_interval` | No | Polling interval (default: 30s) |

## Finding Parameters (LabelDef Format)

The `parameter_id` field uses the **LabelDef format** copied directly from ESPAltherma definition files. This format explicitly specifies the exact register, offset, and converter to use.

### Step 1: Find Your Model's Definition File

1. Go to [ESPAltherma definition files](https://github.com/raomin/ESPAltherma/tree/main/include/def)
2. Find your model's `.h` file (e.g., `ALTHERMA(HYBRID).h`)

### Step 2: Copy the LabelDef Entry

Each line in the definition file has this format:

```c
{registryID, offset, converterID, dataSize, dataType, "Label"}
```

**Example from ALTHERMA(HYBRID).h:**
```c
{0x60,0,304,2,-1,"Leaving water temp. before BUH (R1T)"},
{0x60,2,315,1,-1,"Outdoor air temp."},
{0x62,1,152,1,-1,"Operation Mode"},
{0x20,4,307,1,0,"Thermostat ON/OFF"},
```

### Step 3: Use in Your Config

Copy the entire `{...}` part as your `parameter_id`:

```yaml
sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x60,2,315,1,-1,"Outdoor air temp."}'
    name: "Outdoor Temperature"
```

> **Important:** The parameter_id must be quoted in YAML since it contains special characters.

**Override dataType if needed:** If ESPAltherma's dataType doesn't match the actual data type, you can override it:

```yaml
# If ESPAltherma says dataType=1 but it's actually numeric:
sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x20,0,105,2,-1,"R1T-Outdoor air temp."}'  # Changed 1 to -1
    name: "Outdoor Temperature"
```

### LabelDef Field Reference

| Position | Field | Description |
|----------|-------|-------------|
| 1 | registryID | Heat pump registry address (hex, e.g., 0x60) |
| 2 | offset | Byte offset within registry data |
| 3 | converterID | ESPAltherma converter function number |
| 4 | dataSize | Number of bytes to read (1, 2, or 4) |
| 5 | dataType | Sensor type hint (see table below) |
| 6 | label | Human-readable name |

## Choosing Sensor Type

The **dataType** field (5th value) indicates which ESPHome platform to use:

| dataType | ESPHome Platform | Description |
|----------|------------------|-------------|
| `-1` | `sensor` or `text_sensor` | See label content below |
| `0` | `binary_sensor` | ON/OFF boolean value |
| `1` | `text_sensor` | String/text value |
| `2` | `sensor` | Numeric value |

When dataType is `-1`, check the label name:

| Label Contains | Platform | Examples |
|----------------|----------|----------|
| `temp`, units like `(°C)`, `(A)`, `(V)`, `(kW)`, `(%)` | `sensor` | "Outdoor air temp.", "Voltage (V)" |
| `Mode`, `type`, `Code`, `status` | `text_sensor` | "Operation Mode", "Error Code" |
| `ON/OFF` | `binary_sensor` | "Thermostat ON/OFF" |

**Quick rule:** Numbers with units → `sensor`. States/modes → `text_sensor`. ON/OFF → `binary_sensor`.

## Numeric Sensors

Use `sensor` for temperatures, currents, voltages, and other numeric values:

```yaml
sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x60,2,315,1,-1,"Outdoor air temp."}'
    name: "Outdoor Temperature"
    
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x60,10,303,2,-1,"DHW tank temp. (R5T)"}'
    name: "DHW Tank Temperature"
    
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x60,7,316,1,-1,"INV primary current (A)"}'
    name: "Inverter Current"
```

## Text Sensors

Use `text_sensor` for modes, status strings, and error codes:

```yaml
text_sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x62,1,152,1,-1,"Operation Mode"}'
    name: "Operation Mode"
    
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x60,3,204,1,-1,"Error Code"}'
    name: "Error Code"
```

## Binary Sensors

Use `binary_sensor` for ON/OFF states:

```yaml
binary_sensor:
  - platform: altherma
    altherma_id: heatpump
    parameter_id: '{0x20,4,307,1,0,"Thermostat ON/OFF"}'
    name: "Thermostat Active"
```

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

### Validation error: "Invalid parameter_id format"
- The parameter_id must be in LabelDef format: `{registry,offset,conv,size,type,"label"}`
- Copy the exact format from the ESPAltherma definition file
- Ensure the parameter_id is quoted in YAML

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
- Heat pump returned an error for the registry query
- Verify the registryID exists for your heat pump model
- Check the ESPAltherma definition file for your specific model

### Some sensors always empty
- The parameter might not exist on your heat pump variant
- Check the definition file - some parameters are commented out (disabled by default)
- Try a different registryID from your model's definition file

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
