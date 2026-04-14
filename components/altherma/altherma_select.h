#pragma once

#include "esphome/core/component.h"
#include "esphome/components/select/select.h"
#include "esphome/core/hal.h"

namespace esphome {
namespace altherma {

/**
 * Smart Grid Select for Altherma Heat Pump.
 * 
 * Controls SG1 and SG2 relay outputs for Smart Grid integration.
 * 
 * | Mode           | SG1   | SG2   | Description |
 * |----------------|-------|-------|-------------|
 * | Normal (0)     | open  | open  | Normal operation |
 * | Forced OFF (1) | open  | close | HP forced OFF |
 * | Recommended ON (2) | close | open | HP recommended ON (+5°C setpoint) |
 * | Forced ON (3)  | close | close | HP forced ON (DHW to 70°C) |
 */
class AlthermaSelect : public select::Select, public Component {
 public:
  void setup() override {
    ESP_LOGCONFIG("altherma.select", "Setting up Smart Grid Select");
    ESP_LOGCONFIG("altherma.select", "  SG1 Pin: %d, SG2 Pin: %d", this->sg1_pin_, this->sg2_pin_);
    
    pinMode(this->sg1_pin_, OUTPUT);
    pinMode(this->sg2_pin_, OUTPUT);
    
    // Initialize to Normal mode (both open)
    digitalWrite(this->sg1_pin_, LOW);
    digitalWrite(this->sg2_pin_, LOW);
    
    this->publish_state("Normal");
  }

  void dump_config() override {
    ESP_LOGCONFIG("altherma.select", "Altherma Smart Grid Select:");
    ESP_LOGCONFIG("altherma.select", "  SG1 Pin: %d", this->sg1_pin_);
    ESP_LOGCONFIG("altherma.select", "  SG2 Pin: %d", this->sg2_pin_);
  }

  void set_sg1_pin(int pin) { this->sg1_pin_ = pin; }
  void set_sg2_pin(int pin) { this->sg2_pin_ = pin; }

 protected:
  void control(const std::string &value) override {
    uint8_t mode = 0;
    
    if (value == "Normal") {
      mode = 0;
    } else if (value == "Forced OFF") {
      mode = 1;
    } else if (value == "Recommended ON") {
      mode = 2;
    } else if (value == "Forced ON") {
      mode = 3;
    } else {
      ESP_LOGW("altherma.select", "Unknown Smart Grid mode: %s", value.c_str());
      return;
    }
    
    // Set relay states based on mode
    // SG1: close when mode & 0x02, open otherwise
    // SG2: close when mode & 0x01, open otherwise
    bool sg1_state = (mode & 0x02) != 0;
    bool sg2_state = (mode & 0x01) != 0;
    
    digitalWrite(this->sg1_pin_, sg1_state ? HIGH : LOW);
    digitalWrite(this->sg2_pin_, sg2_state ? HIGH : LOW);
    
    ESP_LOGD("altherma.select", "Smart Grid mode set to %s (SG1=%d, SG2=%d)", 
             value.c_str(), sg1_state, sg2_state);
    
    this->publish_state(value);
  }

  int sg1_pin_{0};
  int sg2_pin_{0};
};

}  // namespace altherma
}  // namespace esphome
