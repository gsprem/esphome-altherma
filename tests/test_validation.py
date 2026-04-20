"""Unit tests for Altherma validation module.

Tests cover LabelDef parsing, security validation, and edge cases.
Run with: python -m pytest tests/test_validation.py -v
"""
import sys
import os
import pytest

# Add components to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'components', 'altherma'))

from validation import (
    parse_labeldef_string,
    validate_parameter_id,
    make_sensor_key,
    escape_label_for_cpp,
    MAX_LABEL_LENGTH,
    MAX_PARAMETER_ID_LENGTH,
)


class TestParseLabeldefString:
    """Tests for parse_labeldef_string() function."""

    # ==================== Valid Input Tests ====================
    
    def test_valid_hex_registry(self):
        """Test parsing with hex registry ID."""
        result = parse_labeldef_string('{0x60,2,315,1,-1,"Outdoor air temp."}')
        assert result is not None
        assert result["registry_id"] == 0x60  # 96
        assert result["offset"] == 2
        assert result["conv_id"] == 315
        assert result["data_size"] == 1
        assert result["data_type"] == -1
        assert result["label"] == "Outdoor air temp."

    def test_valid_decimal_registry(self):
        """Test parsing with decimal registry ID."""
        result = parse_labeldef_string('{96,2,315,1,-1,"Outdoor air temp."}')
        assert result is not None
        assert result["registry_id"] == 96
        assert result["offset"] == 2

    def test_valid_hex_lowercase(self):
        """Test hex parsing is case-insensitive."""
        result = parse_labeldef_string('{0x6a,5,200,2,0,"Test Label"}')
        assert result is not None
        assert result["registry_id"] == 0x6A  # 106

    def test_valid_hex_uppercase(self):
        """Test uppercase hex."""
        result = parse_labeldef_string('{0xFF,0,100,1,1,"Max Registry"}')
        assert result is not None
        assert result["registry_id"] == 255

    def test_valid_data_type_zero(self):
        """Test dataType 0 (binary sensor)."""
        result = parse_labeldef_string('{0x20,4,307,1,0,"Thermostat ON/OFF"}')
        assert result is not None
        assert result["data_type"] == 0

    def test_valid_data_type_one(self):
        """Test dataType 1 (text sensor)."""
        result = parse_labeldef_string('{0x62,1,152,1,1,"Operation Mode"}')
        assert result is not None
        assert result["data_type"] == 1

    def test_valid_data_type_two(self):
        """Test dataType 2 (numeric sensor)."""
        result = parse_labeldef_string('{0x62,11,105,1,2,"Water pressure"}')
        assert result is not None
        assert result["data_type"] == 2

    def test_valid_data_type_negative_one(self):
        """Test dataType -1 (numeric/auto)."""
        result = parse_labeldef_string('{0x60,0,304,2,-1,"Leaving water temp."}')
        assert result is not None
        assert result["data_type"] == -1

    def test_valid_whitespace_variations(self):
        """Test various whitespace patterns."""
        # Extra spaces
        result = parse_labeldef_string('{  0x60 , 2 , 315 , 1 , -1 , "Test"  }')
        assert result is not None
        assert result["label"] == "Test"
        
        # Minimal spaces
        result = parse_labeldef_string('{0x60,2,315,1,-1,"Test"}')
        assert result is not None

    def test_valid_label_with_parentheses(self):
        """Test label containing parentheses."""
        result = parse_labeldef_string('{0x60,10,303,2,-1,"DHW tank temp. (R5T)"}')
        assert result is not None
        assert result["label"] == "DHW tank temp. (R5T)"

    def test_valid_label_with_special_chars(self):
        """Test label with allowed special characters."""
        result = parse_labeldef_string('{0x60,0,100,1,-1,"Flow rate (l/min) <test>"}')
        assert result is not None
        assert "l/min" in result["label"]

    def test_valid_label_with_units(self):
        """Test labels with unit indicators."""
        result = parse_labeldef_string('{0x60,7,316,1,-1,"INV primary current (A)"}')
        assert result is not None
        assert result["label"] == "INV primary current (A)"

    # ==================== Invalid Format Tests ====================

    def test_invalid_none(self):
        """Test None input."""
        assert parse_labeldef_string(None) is None

    def test_invalid_empty_string(self):
        """Test empty string."""
        assert parse_labeldef_string("") is None

    def test_invalid_not_string(self):
        """Test non-string input."""
        assert parse_labeldef_string(123) is None

    def test_invalid_missing_braces(self):
        """Test missing braces."""
        assert parse_labeldef_string('0x60,2,315,1,-1,"Test"') is None
        assert parse_labeldef_string('{0x60,2,315,1,-1,"Test"') is None
        assert parse_labeldef_string('0x60,2,315,1,-1,"Test"}') is None

    def test_invalid_missing_fields(self):
        """Test missing required fields."""
        assert parse_labeldef_string('{0x60,2,315,1,"Test"}') is None  # Missing dataType
        assert parse_labeldef_string('{0x60,2,315,-1,"Test"}') is None  # Missing dataSize
        assert parse_labeldef_string('{0x60,2,-1,"Test"}') is None

    def test_invalid_missing_quotes(self):
        """Test label without quotes."""
        assert parse_labeldef_string('{0x60,2,315,1,-1,Test}') is None
        assert parse_labeldef_string('{0x60,2,315,1,-1,Test"}') is None
        assert parse_labeldef_string('{0x60,2,315,1,-1,"Test}') is None

    def test_invalid_empty_label(self):
        """Test empty label string."""
        assert parse_labeldef_string('{0x60,2,315,1,-1,""}') is None

    def test_invalid_data_type_values(self):
        """Test invalid dataType values (outside -99 to 99 range or 3+ digits)."""
        assert parse_labeldef_string('{0x60,2,315,1,100,"Test"}') is None  # 3 digits
        assert parse_labeldef_string('{0x60,2,315,1,-100,"Test"}') is None  # 4 chars

    # ==================== Boundary Tests ====================

    def test_boundary_registry_id_min(self):
        """Test minimum registry ID (0x00)."""
        result = parse_labeldef_string('{0x00,0,100,1,-1,"Min Registry"}')
        assert result is not None
        assert result["registry_id"] == 0

    def test_boundary_registry_id_max(self):
        """Test maximum registry ID (0xFF)."""
        result = parse_labeldef_string('{0xFF,0,100,1,-1,"Max Registry"}')
        assert result is not None
        assert result["registry_id"] == 255

    def test_boundary_registry_id_overflow(self):
        """Test registry ID > 255."""
        assert parse_labeldef_string('{0x100,0,100,1,-1,"Overflow"}') is None
        assert parse_labeldef_string('{256,0,100,1,-1,"Overflow"}') is None

    def test_boundary_offset_max(self):
        """Test maximum offset (255)."""
        result = parse_labeldef_string('{0x60,255,100,1,-1,"Max Offset"}')
        assert result is not None
        assert result["offset"] == 255

    def test_boundary_offset_overflow(self):
        """Test offset > 255."""
        assert parse_labeldef_string('{0x60,256,100,1,-1,"Overflow"}') is None

    def test_boundary_conv_id_max(self):
        """Test maximum conv_id (999)."""
        result = parse_labeldef_string('{0x60,0,999,1,-1,"Max Conv"}')
        assert result is not None
        assert result["conv_id"] == 999

    def test_boundary_conv_id_overflow(self):
        """Test conv_id > 999."""
        assert parse_labeldef_string('{0x60,0,1000,1,-1,"Overflow"}') is None

    def test_boundary_data_size_valid(self):
        """Test valid data sizes (1-8)."""
        for size in [1, 2, 4, 8]:
            result = parse_labeldef_string(f'{{0x60,0,100,{size},-1,"Test"}}')
            assert result is not None
            assert result["data_size"] == size

    def test_boundary_data_size_invalid(self):
        """Test invalid data sizes."""
        assert parse_labeldef_string('{0x60,0,100,0,-1,"Test"}') is None  # 0 invalid
        assert parse_labeldef_string('{0x60,0,100,9,-1,"Test"}') is None  # 9 invalid

    def test_boundary_label_max_length(self):
        """Test label at max length."""
        label = "A" * MAX_LABEL_LENGTH
        result = parse_labeldef_string(f'{{0x60,0,100,1,-1,"{label}"}}')
        assert result is not None
        assert len(result["label"]) == MAX_LABEL_LENGTH

    def test_boundary_label_over_max_length(self):
        """Test label exceeding max length."""
        label = "A" * (MAX_LABEL_LENGTH + 1)
        assert parse_labeldef_string(f'{{0x60,0,100,1,-1,"{label}"}}') is None

    def test_boundary_parameter_id_max_length(self):
        """Test parameter_id at max length."""
        # Create a long but valid parameter_id
        label = "A" * 50  # Keep label reasonable
        param_id = f'{{0x60,0,100,1,-1,"{label}"}}'
        if len(param_id) <= MAX_PARAMETER_ID_LENGTH:
            result = parse_labeldef_string(param_id)
            assert result is not None

    def test_boundary_parameter_id_over_max_length(self):
        """Test parameter_id exceeding max length."""
        label = "A" * (MAX_PARAMETER_ID_LENGTH + 50)
        assert parse_labeldef_string(f'{{0x60,0,100,1,-1,"{label}"}}') is None

    # ==================== Security Tests (Injection Prevention) ====================

    def test_security_reject_quotes_in_label(self):
        """Test rejection of quotes in label (prevents string termination)."""
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test\\"Inject"}') is None
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test"Inject"}') is None

    def test_security_reject_backslash_in_label(self):
        """Test rejection of backslash in label (prevents escape sequences)."""
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test\\nInject"}') is None
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test\\\\Inject"}') is None

    def test_security_reject_braces_in_label(self):
        """Test rejection of braces in label (prevents struct injection)."""
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test{Inject"}') is None
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test}Inject"}') is None

    def test_security_reject_semicolon_in_label(self):
        """Test rejection of semicolon in label (prevents statement injection)."""
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test;Inject"}') is None

    def test_security_reject_cpp_comment(self):
        """Test that // in labels is safe (inside C++ string literals, not a comment)."""
        # Note: // inside a string literal does NOT start a comment in C++
        # So this is actually safe and should be allowed
        result = parse_labeldef_string('{0x60,0,100,1,-1,"Test//Note"}')
        assert result is not None
        assert result["label"] == "Test//Note"

    def test_security_reject_newlines(self):
        """Test rejection of newline characters."""
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test\nInject"}') is None
        assert parse_labeldef_string('{0x60,0,100,1,-1,"Test\rInject"}') is None


class TestValidateParameterId:
    """Tests for validate_parameter_id() function."""

    def test_valid_returns_normalized(self):
        """Test valid input returns normalized string."""
        result = validate_parameter_id('{0x60,2,315,1,-1,"Test"}')
        assert result == '{0x60,2,315,1,-1,"Test"}'

    def test_valid_strips_whitespace(self):
        """Test whitespace is stripped."""
        result = validate_parameter_id('  {0x60,2,315,1,-1,"Test"}  ')
        assert result == '{0x60,2,315,1,-1,"Test"}'

    def test_invalid_empty_raises(self):
        """Test empty string raises cv.Invalid."""
        # We need to import cv to check for the exception
        import esphome.config_validation as cv
        with pytest.raises(cv.Invalid):
            validate_parameter_id("")

    def test_invalid_format_raises(self):
        """Test invalid format raises cv.Invalid."""
        import esphome.config_validation as cv
        with pytest.raises(cv.Invalid):
            validate_parameter_id("not a labeldef")


class TestMakeSensorKey:
    """Tests for make_sensor_key() function."""

    def test_basic_key_generation(self):
        """Test basic key generation."""
        parsed = {"registry_id": 96, "offset": 2}
        assert make_sensor_key(parsed) == "96_2"

    def test_key_with_zero_offset(self):
        """Test key with offset 0."""
        parsed = {"registry_id": 96, "offset": 0}
        assert make_sensor_key(parsed) == "96_0"

    def test_key_with_max_values(self):
        """Test key with max registry and offset."""
        parsed = {"registry_id": 255, "offset": 255}
        assert make_sensor_key(parsed) == "255_255"

    def test_key_uniqueness(self):
        """Test that same registry+offset produces same key."""
        parsed1 = {"registry_id": 96, "offset": 3, "label": "Error Code"}
        parsed2 = {"registry_id": 96, "offset": 3, "label": "Different Label"}
        assert make_sensor_key(parsed1) == make_sensor_key(parsed2)

    def test_different_locations_different_keys(self):
        """Test that different registry/offset produces different keys."""
        parsed1 = {"registry_id": 16, "offset": 5, "label": "Error Code"}
        parsed2 = {"registry_id": 96, "offset": 3, "label": "Error Code"}
        assert make_sensor_key(parsed1) != make_sensor_key(parsed2)


class TestEscapeLabelForCpp:
    """Tests for escape_label_for_cpp() function."""

    def test_no_escape_needed(self):
        """Test label without special chars."""
        assert escape_label_for_cpp("Outdoor air temp.") == "Outdoor air temp."

    def test_preserves_allowed_chars(self):
        """Test allowed special chars are preserved."""
        assert escape_label_for_cpp("Flow (l/min)") == "Flow (l/min)"
        assert escape_label_for_cpp("Temp <high>") == "Temp <high>"


class TestIntegration:
    """Integration tests for the full validation pipeline."""

    def test_full_pipeline_valid(self):
        """Test complete pipeline with valid input."""
        param_id = '{0x60,2,315,1,-1,"Outdoor air temp."}'
        
        # Validate
        validated = validate_parameter_id(param_id)
        
        # Parse
        parsed = parse_labeldef_string(validated)
        assert parsed is not None
        
        # Generate key
        key = make_sensor_key(parsed)
        assert key == "96_2"
        
        # Escape for C++
        escaped = escape_label_for_cpp(parsed["label"])
        assert escaped == "Outdoor air temp."

    def test_duplicate_labels_unique_keys(self):
        """Test that duplicate labels get unique keys."""
        # Same label "Error Code" at different locations
        param1 = '{0x10,5,204,1,-1,"Error Code"}'
        param2 = '{0x60,3,204,1,-1,"Error Code"}'
        
        parsed1 = parse_labeldef_string(param1)
        parsed2 = parse_labeldef_string(param2)
        
        key1 = make_sensor_key(parsed1)
        key2 = make_sensor_key(parsed2)
        
        # Keys must be different even though labels are the same
        assert key1 != key2
        assert key1 == "16_5"
        assert key2 == "96_3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
