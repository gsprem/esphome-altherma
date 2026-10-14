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
// 2. Make buff static to avoid ODR violation
#ifdef Serial
#undef Serial
#endif
#define Serial mqttSerial

#define buff altherma_converter_buff_

// From https://github.com/raomin/ESPAltherma.git 
// Commit ref 281033c80ec8ba5b758c0cbd17e795fb8aeb3e0f
#include "ESPAltherma.converters.h"
#undef buff
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

  for (const uint8_t registry_id : this->unique_registries_) {
    this->query_and_process_registry_(registry_id);
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
    if (!this->available()) {
      yield();
      continue;
    }

    if (!this->read_response_byte_(buffer, len, expected_len)) {
      return false;
    }
  }

  if (len != expected_len) {
    if (len == 0) {
      ESP_LOGW(TAG, "Timeout - no response from heat pump");
    } else {
      ESP_LOGW(TAG, "Timeout, got %u/%u bytes", static_cast<unsigned int>(len),
               static_cast<unsigned int>(expected_len));
    }
    return false;
  }

  return true;
}

bool AlthermaComponent::read_response_byte_(uint8_t *buffer, size_t &len, size_t &expected_len) {
  if (len >= RX_BUFFER_SIZE) {
    ESP_LOGE(TAG, "Buffer overflow prevented - response too large");
    return false;
  }

  const int next_byte = this->read();
  if (next_byte < 0) {
    return false;
  }

  buffer[len++] = static_cast<uint8_t>(next_byte);
  ESP_LOGVV(TAG, "RX[%u] = 0x%02X", static_cast<unsigned int>(len - 1), buffer[len - 1]);

  if (len == LENGTH_BYTE_INDEX + 1 && !this->update_expected_response_length_(buffer, expected_len)) {
    return false;
  }

  return !this->is_heat_pump_error_response_(buffer, len);
}

bool AlthermaComponent::update_expected_response_length_(const uint8_t *buffer, size_t &expected_len) const {
  // The length field counts bytes after the first two frame bytes.
  expected_len = static_cast<size_t>(buffer[LENGTH_BYTE_INDEX]) + 2;
  if (expected_len < DATA_OFFSET + 1) {
    ESP_LOGW(TAG, "Invalid response length %u", static_cast<unsigned int>(expected_len));
    return false;
  }

  if (expected_len > RX_BUFFER_SIZE) {
    ESP_LOGE(TAG, "Invalid response length %u exceeds buffer size %u",
             static_cast<unsigned int>(expected_len), static_cast<unsigned int>(RX_BUFFER_SIZE));
    return false;
  }

  return true;
}

bool AlthermaComponent::is_heat_pump_error_response_(const uint8_t *buffer, size_t len) const {
  if (len != 2 || buffer[0] != ERROR_RESPONSE_BYTE1 || buffer[1] != ERROR_RESPONSE_BYTE2) {
    return false;
  }

  ESP_LOGW(TAG, "Heat pump returned error 0x%02X 0x%02X (command not understood)",
           ERROR_RESPONSE_BYTE1, ERROR_RESPONSE_BYTE2);
  return true;
}

void AlthermaComponent::query_and_process_registry_(uint8_t registry_id) {
  size_t frame_len = 0;
  if (!this->query_registry_(registry_id, this->rx_buffer_, frame_len)) {
    ESP_LOGW(TAG, "Failed to query registry 0x%02X", registry_id);
    return;
  }

  this->process_registry_data_(registry_id, frame_len);
}

void AlthermaComponent::process_registry_data_(uint8_t registry_id, size_t frame_len) {
  for (size_t i = 0; i < labelDefs_size; i++) {
    if (static_cast<uint8_t>(labelDefs[i].registryID) == registry_id) {
      this->process_label_(registry_id, labelDefs[i], frame_len);
    }
  }
}

void AlthermaComponent::process_label_(uint8_t registry_id, LabelDef &label, size_t frame_len) {
  if (frame_len < DATA_OFFSET + 1) {
    ESP_LOGW(TAG, "Registry 0x%02X frame is too short to contain a payload", registry_id);
    return;
  }

  const size_t data_offset = static_cast<size_t>(label.offset) + DATA_OFFSET;
  const size_t data_size = static_cast<size_t>(label.dataSize);
  // Exclude the trailing CRC when checking the converter's input range.
  const size_t frame_data_end = frame_len - 1;
  if (label.dataSize <= 0 || data_offset > frame_data_end || data_size > frame_data_end - data_offset) {
    ESP_LOGW(TAG, "Registry 0x%02X frame too short for label '%s' (offset %u, size %u, frame %u)",
             registry_id, label.label, static_cast<unsigned int>(data_offset), static_cast<unsigned int>(data_size),
             static_cast<unsigned int>(frame_len));
    return;
  }

  unsigned char *input = this->rx_buffer_ + data_offset;
  ESP_LOGVV(TAG, "Registry 0x%02X label '%s' raw data:", registry_id, label.label);
  for (size_t byte = 0; byte < data_size; byte++) {
    ESP_LOGVV(TAG, "  [%u] 0x%02X", static_cast<unsigned int>(byte), input[byte]);
  }

  this->converter_->convert(&label, input);
  ESP_LOGVV(TAG, "Registry 0x%02X label '%s' decoded as '%s'", registry_id, label.label, label.asString);
}

bool AlthermaComponent::validate_response_(const uint8_t *buffer, size_t len, uint8_t registry_id) const {
  if (buffer == nullptr || len < DATA_OFFSET + 1) {
    ESP_LOGW(TAG, "Response for registry 0x%02X is too short (%u bytes)", registry_id,
             static_cast<unsigned int>(len));
    return false;
  }

  if (buffer[0] != RESPONSE_HEADER) {
    ESP_LOGW(TAG, "Invalid response header for registry 0x%02X: 0x%02X", registry_id, buffer[0]);
    return false;
  }

  if (buffer[1] != registry_id) {
    ESP_LOGW(TAG, "Response registry mismatch: requested 0x%02X, received 0x%02X", registry_id, buffer[1]);
    return false;
  }

  if (static_cast<size_t>(buffer[LENGTH_BYTE_INDEX]) + 2 != len) {
    ESP_LOGW(TAG, "Response length field mismatch for registry 0x%02X", registry_id);
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

  size_t discarded_bytes = 0;
  const size_t pending_bytes = this->available();
  for (size_t i = 0; i < pending_bytes; i++) {
    if (this->read() < 0) {
      break;
    }
    discarded_bytes++;
  }
  if (discarded_bytes > 0) {
    ESP_LOGW(TAG, "Discarded %u stale UART bytes before registry 0x%02X",
             static_cast<unsigned int>(discarded_bytes), registry_id);
  }

  ESP_LOGV(TAG, "Querying registry 0x%02X...", registry_id);
  ESP_LOGVV(TAG, "TX registry 0x%02X: %02X %02X %02X %02X", registry_id, cmd[0], cmd[1], cmd[2], cmd[3]);

  this->write_array(cmd, cmd_len);
  this->flush();

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
  if (labelDefs_size == 0) {
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
