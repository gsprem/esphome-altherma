#include "altherma.h"
#include "esphome/core/log.h"
#include "esphome/core/helpers.h"
#include <cstdlib>   // For strtof
#include <cstring>   // For strcmp
#include <cmath>     // For NAN
#include <algorithm> // For std::find

// Silent stubs - ESPAltherma's headers call Serial/mqttSerial for debug output
struct NullSerial {
  template <typename... Args>
  void print(Args...) {}
  template <typename... Args>
  void println(Args...) {}
  template <typename... Args>
  void printf(Args...) {}
};
static NullSerial mqttSerial;

// Include ESPAltherma's converters.h with workarounds:
// 1. Redirect Serial to our null sink
// 2. Use dummy labelDefs array for range-for compilation
// 3. Make buff static to avoid ODR violation
#ifdef Serial
#undef Serial
#endif
#define Serial mqttSerial

static LabelDef labelDefs_dummy_[] = {LabelDef(0, 0, 0, 0, 0, "")};
#define labelDefs labelDefs_dummy_
#define buff altherma_converter_buff_
#include "ESPAltherma/include/converters.h"
#undef buff
#undef labelDefs
#undef Serial

namespace esphome {
namespace altherma {

static const char *const TAG = "altherma";

// ==================== Lifecycle Methods ====================

// Destructor must be defined here where Converter is complete
AlthermaComponent::~AlthermaComponent() {
  if (this->converter_ != nullptr) {
    delete this->converter_;
    this->converter_ = nullptr;
  }
}

void AlthermaComponent::setup() {
  ESP_LOGCONFIG(TAG, "Setting up Altherma...");

  // Create converter instance
  this->converter_ = new (std::nothrow) Converter();
  if (!this->is_converter_ready_()) {
    ESP_LOGE(TAG, "Failed to allocate Converter - out of memory!");
    this->mark_failed();
    return;
  }

  // Build list of unique registries from the global labelDefs array.
  // A "registry" is a memory page/register in the heat pump that holds multiple data values.
  // Each label (sensor) reads from a specific registry at a given offset.
  // Multiple labels may share the same registry (e.g., temperatures, pressures).
  // We deduplicate registry IDs to avoid redundant serial queries - each registry
  // is queried once per update cycle, then all labels extract their values from it.
  this->build_registry_list_();

  if (this->unique_registries_.empty()) {
    ESP_LOGW(TAG, "No registries to query  - no sensors configured");
  } else {
    ESP_LOGD(TAG, "Found %d unique registries to query", this->unique_registries_.size());
  }

  this->initialized_ = true;
}

void AlthermaComponent::build_registry_list_() {
  // Use O(n) algorithm with temporary set for deduplication
  std::unordered_set<uint8_t> seen;
  seen.reserve(labelDefs_size);  // Reserve space for efficiency

  for (size_t i = 0; i < labelDefs_size; i++) {
    const uint8_t reg_id = static_cast<uint8_t>(labelDefs[i].registryID);

    // Only add if not already seen
    if (seen.insert(reg_id).second) {
      this->unique_registries_.push_back(reg_id);
    }
  }
}

void AlthermaComponent::loop() {
  // Nothing to do in loop - we use polling via update()
}

void AlthermaComponent::update() {
  // Defensive checks
  if (!this->initialized_ || this->unique_registries_.empty()) {
    return;
  }

  if (!this->is_converter_ready_()) {
    ESP_LOGE(TAG, "Converter not initialized!");
    return;
  }

  ESP_LOGD(TAG, "Querying %d registries...", this->unique_registries_.size());

  // Query all registries
  for (const uint8_t registry_id : this->unique_registries_) {
    size_t len = 0;
    if (this->query_registry_(registry_id, this->rx_buffer_, len)) {
      // Process data using ESPAltherma's converter
      // We iterate ourselves since ESPAltherma's getLabels uses range-for on labelDefs
      const char reg_id_signed = static_cast<char>(registry_id);

      for (size_t i = 0; i < labelDefs_size; i++) {
        if (labelDefs[i].registryID == reg_id_signed) {
          // Bounds check for buffer access
          const size_t data_offset = labelDefs[i].offset + DATA_OFFSET;
          if (data_offset < len) {
            unsigned char *input = this->rx_buffer_ + data_offset;
            this->converter_->convert(&labelDefs[i], input);
          } else {
            ESP_LOGW(TAG, "Data offset %d exceeds buffer length %d for label %s", 
                     data_offset, len, labelDefs[i].label);
          }
        }
      }
    } else {
      ESP_LOGW(TAG, "Failed to query registry 0x%02X", registry_id);
    }
    
    // Small delay between queries to avoid overwhelming the heat pump
    delay(INTER_QUERY_DELAY_MS);
  }

  // Publish all values
  this->publish_values_();
}

void AlthermaComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Altherma Heat Pump:");
  ESP_LOGCONFIG(TAG, "  Protocol: I");
  ESP_LOGCONFIG(TAG, "  Unique registries: %d", this->unique_registries_.size());
  ESP_LOGCONFIG(TAG, "  Sensors: %d", this->sensors_.size());
  ESP_LOGCONFIG(TAG, "  Binary sensors: %d", this->binary_sensors_.size());
  ESP_LOGCONFIG(TAG, "  Text sensors: %d", this->text_sensors_.size());
  LOG_UPDATE_INTERVAL(this);
  this->check_uart_settings(UART_BAUD_RATE, UART_STOP_BITS, UART_PARITY, UART_DATA_BITS);
}

// ==================== Sensor Registration ====================

void AlthermaComponent::register_sensor(const std::string &parameter_id, sensor::Sensor *sensor) {
  if (sensor != nullptr) {
    this->sensors_[parameter_id] = sensor;
    ESP_LOGV(TAG, "Registered sensor: %s", parameter_id.c_str());
  }
}

void AlthermaComponent::register_binary_sensor(const std::string &parameter_id,
                                                binary_sensor::BinarySensor *sensor) {
  if (sensor != nullptr) {
    this->binary_sensors_[parameter_id] = sensor;
    ESP_LOGV(TAG, "Registered binary sensor: %s", parameter_id.c_str());
  }
}

void AlthermaComponent::register_text_sensor(const std::string &parameter_id,
                                              text_sensor::TextSensor *sensor) {
  if (sensor != nullptr) {
    this->text_sensors_[parameter_id] = sensor;
    ESP_LOGV(TAG, "Registered text sensor: %s", parameter_id.c_str());
  }
}

// ==================== CRC & Protocol Helpers ====================

uint8_t AlthermaComponent::calculate_crc_(const uint8_t *data, size_t len) const {
  if (data == nullptr || len == 0) {
    return 0;
  }

  uint8_t crc = 0;
  for (size_t i = 0; i < len; i++) {
    crc += data[i];
  }
  return ~crc;  // Bitwise NOT
}

// ==================== Command & Response Handling ====================

void AlthermaComponent::build_command_(uint8_t registry_id, uint8_t *cmd, size_t &cmd_len) const {
  // Protocol I command format
  cmd[0] = CMD_HEADER;
  cmd[1] = CMD_PREFIX;
  cmd[2] = registry_id;
  cmd[3] = this->calculate_crc_(cmd, 3);
  cmd_len = CMD_LENGTH;
}

bool AlthermaComponent::read_response_(uint8_t *buffer, size_t &len, uint32_t start_time) {
  size_t expected_len = len;  // Input: expected length
  len = 0;  // Reset to track actual bytes read

  while ((len < expected_len) && (millis() - start_time < SERIAL_TIMEOUT_MS)) {
    if (this->available()) {
      // Buffer overflow protection
      if (len >= RX_BUFFER_SIZE) {
        ESP_LOGE(TAG, "Buffer overflow prevented - response too large");
        return false;
      }

      buffer[len++] = this->read();

      // Update expected length from response byte 2
      if (len == LENGTH_BYTE_INDEX + 1) {
        expected_len = buffer[LENGTH_BYTE_INDEX] + 2;
        
        // Validate expected length doesn't exceed buffer
        if (expected_len > RX_BUFFER_SIZE) {
          ESP_LOGE(TAG, "Invalid response length %d exceeds buffer size %d", 
                   expected_len, RX_BUFFER_SIZE);
          return false;
        }
      }

      // Check for error response
      if (len == 2 && buffer[0] == ERROR_RESPONSE_BYTE1 && buffer[1] == ERROR_RESPONSE_BYTE2) {
        ESP_LOGW(TAG, "Heat pump returned error 0x%02X 0x%02X (command not understood)",
                 ERROR_RESPONSE_BYTE1, ERROR_RESPONSE_BYTE2);
        return false;
      }
    }
    yield();  // Allow other tasks to run
  }

  // Check for timeout
  if (millis() - start_time >= SERIAL_TIMEOUT_MS) {
    if (len == 0) {
      ESP_LOGW(TAG, "Timeout - no response from heat pump");
    } else {
      ESP_LOGW(TAG, "Timeout, got %d/%d bytes", len, expected_len);
    }
    return false;
  }

  return true;
}

bool AlthermaComponent::validate_response_(const uint8_t *buffer, size_t len, uint8_t registry_id) const {
  if (len == 0) {
    return false;
  }

  const uint8_t received_crc = buffer[len - 1];
  const uint8_t calculated_crc = this->calculate_crc_(buffer, len - 1);
  
  if (calculated_crc != received_crc) {
    ESP_LOGW(TAG, "CRC error on registry 0x%02X (expected 0x%02X, got 0x%02X)",
             registry_id, calculated_crc, received_crc);
    return false;
  }

  return true;
}

bool AlthermaComponent::query_registry_(uint8_t registry_id, uint8_t *buffer, size_t &len) {
  if (buffer == nullptr) {
    ESP_LOGE(TAG, "Null buffer passed to query_registry_");
    return false;
  }

  // Build and send command
  uint8_t cmd[MAX_COMMAND_SIZE];
  size_t cmd_len;
  this->build_command_(registry_id, cmd, cmd_len);
  
  ESP_LOGV(TAG, "Querying registry 0x%02X...", registry_id);
  this->flush();
  this->write_array(cmd, cmd_len);

  // Read response
  const uint32_t start_time = millis();
  len = INITIAL_REPLY_LENGTH;
  
  if (!this->read_response_(buffer, len, start_time)) {
    return false;
  }

  // Validate CRC
  if (!this->validate_response_(buffer, len, registry_id)) {
    return false;
  }

  ESP_LOGV(TAG, "Registry 0x%02X: received %d bytes, CRC OK", registry_id, len);
  return true;
}

// ==================== Data Parsing ====================

bool AlthermaComponent::parse_numeric_value_(const char *str, float &value) const {
  if (str == nullptr || str[0] == '\0') {
    return false;
  }

  // Skip non-numeric strings like "OFF", "ON", "---", etc.
  if (str[0] == '-' && str[1] == '-') {
    return false;  // "---" marker
  }
  
  char *end;
  value = strtof(str, &end);
  
  // Check if conversion was successful (end moved past start)
  if (end == str || *end != '\0') {
    return false;
  }

  // Check for overflow/underflow (strtof returns ±HUGE_VALF on overflow)
  if (value == HUGE_VALF || value == -HUGE_VALF) {
    ESP_LOGW(TAG, "Numeric value overflow/underflow for string: %s", str);
    return false;
  }

  return true;
}

// ==================== Data Publishing ====================

void AlthermaComponent::publish_sensor_(const char *parameter_id, const char *value) {
  auto sensor_it = this->sensors_.find(parameter_id);
  if (sensor_it == this->sensors_.end() || sensor_it->second == nullptr) {
    return;  // Sensor not registered
  }

  float num_value = 0.0f;
  if (this->parse_numeric_value_(value, num_value)) {
    sensor_it->second->publish_state(num_value);
    ESP_LOGV(TAG, "Published sensor '%s': %.2f", parameter_id, num_value);
  }
}

void AlthermaComponent::publish_binary_sensor_(const char *parameter_id, const char *value) {
  auto binary_it = this->binary_sensors_.find(parameter_id);
  if (binary_it == this->binary_sensors_.end() || binary_it->second == nullptr) {
    return;  // Sensor not registered
  }

  // Interpret as ON if "ON", "Heating", "Cooling", or non-zero number
  bool state = false;
  if (strcmp(value, "ON") == 0 || 
      strcmp(value, "Heating") == 0 || 
      strcmp(value, "Cooling") == 0) {
    state = true;
  } else {
    float num = 0.0f;
    if (this->parse_numeric_value_(value, num) && num != 0.0f) {
      state = true;
    }
  }
  
  binary_it->second->publish_state(state);
  ESP_LOGV(TAG, "Published binary sensor '%s': %s", parameter_id, state ? "ON" : "OFF");
}

void AlthermaComponent::publish_text_sensor_(const char *parameter_id, const char *value) {
  auto text_it = this->text_sensors_.find(parameter_id);
  if (text_it == this->text_sensors_.end() || text_it->second == nullptr) {
    return;  // Sensor not registered
  }

  text_it->second->publish_state(value);
  ESP_LOGV(TAG, "Published text sensor '%s': %s", parameter_id, value);
}

void AlthermaComponent::publish_values_() {
  if (labelDefs == nullptr || labelDefs_size == 0) {
    ESP_LOGW(TAG, "No labelDefs available for publishing");
    return;
  }

  // Iterate through all labels and publish to registered sensors
  // Key format: "registryID_offset" (e.g., "96_2") - matches Python make_sensor_key()
  char sensor_key[16];
  
  for (size_t i = 0; i < labelDefs_size; i++) {
    const LabelDef &def = labelDefs[i];
    const char *value = def.asString;
    
    // Skip empty values
    if (value == nullptr || value[0] == '\0') {
      continue;
    }
    
    // Construct unique key from registry_id and offset
    // Cast to uint8_t since registryID is signed char but represents 0x00-0xFF
    snprintf(sensor_key, sizeof(sensor_key), "%u_%u", 
             static_cast<uint8_t>(def.registryID), 
             static_cast<uint8_t>(def.offset));
    
    // Publish to all registered sensor types
    this->publish_sensor_(sensor_key, value);
    this->publish_binary_sensor_(sensor_key, value);
    this->publish_text_sensor_(sensor_key, value);
  }
}

}  // namespace altherma
}  // namespace esphome
