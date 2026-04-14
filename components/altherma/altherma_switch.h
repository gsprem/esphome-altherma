#pragma once

#include "esphome/core/component.h"
#include "esphome/components/switch/switch.h"
#include "esphome/core/hal.h"

namespace esphome {
namespace altherma {

class AlthermaSwitch : public switch_::Switch, public Component {
 public:
  void setup() override {
    ESP_LOGCONFIG("altherma.switch", "Setting up Altherma Switch on pin %d", this->pin_);
    pinMode(this->pin_, OUTPUT);
    // Initialize to OFF
    digitalWrite(this->pin_, LOW);
    this->publish_state(false);
  }

  void dump_config() override {
    ESP_LOGCONFIG("altherma.switch", "Altherma Thermostat Switch:");
    ESP_LOGCONFIG("altherma.switch", "  Pin: %d", this->pin_);
  }

  void set_pin(int pin) { this->pin_ = pin; }

 protected:
  void write_state(bool state) override {
    digitalWrite(this->pin_, state ? HIGH : LOW);
    this->publish_state(state);
  }

  int pin_{0};
};

}  // namespace altherma
}  // namespace esphome
