"""ESPAltherma Installation Management.

This module handles cloning, validating, and managing the ESPAltherma
repository as a build-time dependency. Model definitions are generated
at install time by parsing ESPAltherma header files.
"""
from typing import List, Dict, Any, Optional
import os
import re
import json
import subprocess
import logging
import shutil
from pathlib import Path

import esphome.config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Repository configuration
ESPALTHERMA_REPO_URL = "https://github.com/raomin/ESPAltherma.git"
ESPALTHERMA_DIR_NAME = "ESPAltherma"
ESPALTHERMA_COMMIT_HASH = "281033c80ec8ba5b758c0cbd17e795fb8aeb3e0f"

# Git operation settings
GIT_CLONE_TIMEOUT_SECONDS = 60

# ESPAltherma interface validation
EXPECTED_LABELDEF_FIELDS = [
    "registryID",
    "offset",
    "convid",
    "dataSize",
    "dataType",
    "label",
    "asString",
]
EXPECTED_CONVERTER_METHOD = "readRegistryValues"


class ESPAlthermaError(Exception):
    """Base exception for ESPAltherma-related errors."""
    pass


class ESPAlthermaCloneError(ESPAlthermaError):
    """Raised when cloning ESPAltherma repository fails."""
    pass


class ESPAlthermaCompatibilityError(ESPAlthermaError):
    """Raised when ESPAltherma interface is incompatible."""
    pass


# ==================== Directory & File Utilities ====================


def get_espaltherma_directory(component_dir: str) -> str:
    """Get the absolute path to the ESPAltherma directory.
    
    Args:
        component_dir: Path to the component directory.
    
    Returns:
        str: Absolute path to ESPAltherma directory.
    """
    return os.path.join(component_dir, ESPALTHERMA_DIR_NAME)


def _validate_file_exists(file_path: str, description: str) -> None:
    """Validate that a required file exists.
    
    Args:
        file_path: Path to the file to check.
        description: Human-readable description for error messages.
        
    Raises:
        ESPAlthermaCompatibilityError: If file does not exist.
    """
    if not os.path.isfile(file_path):
        raise ESPAlthermaCompatibilityError(
            f"Required file missing: {description} at {file_path}"
        )


def _remove_directory_safe(directory: str) -> None:
    """Safely remove a directory and its contents.
    
    Args:
        directory: Path to directory to remove.
    """
    try:
        shutil.rmtree(directory)
        _LOGGER.debug("Removed directory: %s", directory)
    except OSError as e:
        _LOGGER.warning("Failed to remove directory %s: %s", directory, e)


# ==================== Git Operations ====================


def _run_git_command(
    args: List[str],
    timeout: int,
    operation_name: str,
) -> subprocess.CompletedProcess:
    """Run a git command with timeout and error handling.
    
    Args:
        args: Command arguments to pass to git.
        timeout: Timeout in seconds.
        operation_name: Description of operation for error messages.
        
    Returns:
        CompletedProcess: Result of the git command.
        
    Raises:
        ESPAlthermaCloneError: If git command fails.
    """
    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired as e:
        raise ESPAlthermaCloneError(
            f"Git {operation_name} timed out after {timeout}s. "
            f"Check network connection or increase timeout."
        ) from e
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error"
        raise ESPAlthermaCloneError(
            f"Git {operation_name} failed: {error_msg}"
        ) from e
    except FileNotFoundError as e:
        raise ESPAlthermaCloneError(
            "Git command not found. Please install git to use this component."
        ) from e


def _verify_header_file(
    file_path: str,
    expected_content: List[str],
    description: str,
) -> bool:
    """Verify that a header file contains expected interface elements.
    
    Args:
        file_path: Path to the header file.
        expected_content: List of strings that must be present.
        description: Description for logging.
        
    Returns:
        bool: True if all expected content found, False otherwise.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        missing = [item for item in expected_content if item not in content]
        if missing:
            _LOGGER.warning(
                "%s missing expected elements: %s",
                description,
                ", ".join(missing),
            )
            return False
        return True
        
    except IOError as e:
        _LOGGER.error("Cannot read %s: %s", file_path, e)
        return False


def verify_espaltherma_compatibility(espaltherma_dir: str) -> bool:
    """Verify that ESPAltherma headers have the expected interface.
    
    Checks that critical header files exist and contain required methods
    and structures for compatibility with this component.
    
    Args:
        espaltherma_dir: Path to ESPAltherma directory.
        
    Returns:
        bool: True if compatible, False otherwise.
    """
    include_dir = os.path.join(espaltherma_dir, "include")
    
    # Validate directory structure
    if not os.path.isdir(include_dir):
        _LOGGER.error("ESPAltherma include directory not found: %s", include_dir)
        return False
    
    # Check LabelDef header
    labeldef_path = os.path.join(include_dir, "labeldef.h")
    if not _verify_header_file(
        labeldef_path,
        EXPECTED_LABELDEF_FIELDS,
        "LabelDef header",
    ):
        return False
    
    # Check Converter header
    converter_path = os.path.join(include_dir, "converters.h")
    if not _verify_header_file(
        converter_path,
        [EXPECTED_CONVERTER_METHOD],
        "Converter header",
    ):
        return False
    
    return True


def _clone_espaltherma_repository(target_dir: str) -> None:
    """Clone the ESPAltherma repository to the target directory.
    
    Args:
        target_dir: Directory where repository will be cloned.
        
    Raises:
        ESPAlthermaCloneError: If cloning fails.
    """
    _LOGGER.info(
        "Cloning ESPAltherma (commit %s)...",
        ESPALTHERMA_COMMIT_HASH[:8],
    )
    
    # Clone repository
    _run_git_command(
        ["git", "clone", ESPALTHERMA_REPO_URL, target_dir],
        timeout=GIT_CLONE_TIMEOUT_SECONDS,
        operation_name="clone",
    )
    
    # Checkout specific commit
    _run_git_command(
        ["git", "-C", target_dir, "checkout", ESPALTHERMA_COMMIT_HASH],
        timeout=GIT_CLONE_TIMEOUT_SECONDS,
        operation_name="checkout",
    )
    
    _LOGGER.info("ESPAltherma cloned successfully")


# ==================== Installation Management ====================


def _is_installation_valid(espaltherma_dir: str) -> bool:
    """Check if existing ESPAltherma installation is valid.
    
    Args:
        espaltherma_dir: Path to ESPAltherma directory.
        
    Returns:
        bool: True if installation is valid and compatible.
    """
    labeldef_path = os.path.join(espaltherma_dir, "include", "labeldef.h")
    
    if not os.path.isfile(labeldef_path):
        _LOGGER.warning(
            "ESPAltherma directory exists but missing files, re-cloning..."
        )
        return False
    
    if not verify_espaltherma_compatibility(espaltherma_dir):
        _LOGGER.warning(
            "ESPAltherma compatibility check failed, re-cloning..."
        )
        return False
    
    _LOGGER.debug("ESPAltherma found at %s", espaltherma_dir)
    return True


# ==================== Definition Generation ====================


def _parse_label_def(line: str) -> Optional[Dict[str, Any]]:
    """Parse a LabelDef line from an ESPAltherma definition file."""
    is_commented = line.strip().startswith('//')
    if is_commented:
        line = line.strip()[2:].strip()
    
    pattern = r'^\s*\{(0x[0-9a-fA-F]+|[0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*(-?[0-9]+)\s*,\s*"([^"]+)"\s*\}'
    match = re.match(pattern, line)
    if not match:
        return None
    
    registry_id = int(match.group(1), 16) if match.group(1).startswith('0x') else int(match.group(1))
    return {
        "registry_id": registry_id,
        "offset": int(match.group(2)),
        "conv_id": int(match.group(3)),
        "data_size": int(match.group(4)),
        "data_type": int(match.group(5)),
        "label": match.group(6),
        "enabled": not is_commented,
    }


def _parse_definition_file(filepath: Path) -> Dict[str, Any]:
    """Parse an ESPAltherma definition file and extract all LabelDef entries."""
    labels = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            label_def = _parse_label_def(line_stripped)
            if label_def:
                labels.append(label_def)
    
    protocol = "S" if "PROTOCOL_S" in filepath.name else "I"
    return {
        "name": filepath.stem,
        "description": filepath.stem,
        "protocol": protocol,
        "labels": labels,
    }


def _scan_definition_files(espaltherma_dir: str) -> Dict[str, Dict[str, Any]]:
    """Scan ESPAltherma include/def directory for all definition files."""
    def_dir = Path(espaltherma_dir) / "include" / "def"
    if not def_dir.exists():
        raise FileNotFoundError(f"Definition directory not found: {def_dir}")
    
    models = {}
    
    for filepath in def_dir.glob("*.h"):
        if filepath.name == "labeldef.h":
            continue
        try:
            model = _parse_definition_file(filepath)
            if model["labels"]:
                models[model["name"]] = model
        except Exception as e:
            _LOGGER.warning("Failed to parse %s: %s", filepath.name, e)
    
    for locale_dir in def_dir.iterdir():
        if locale_dir.is_dir() and locale_dir.name in ["German", "French", "Spanish"]:
            for filepath in locale_dir.glob("*.h"):
                try:
                    model = _parse_definition_file(filepath)
                    if model["labels"]:
                        locale_name = f"{locale_dir.name}/{model['name']}"
                        model["name"] = locale_name
                        models[locale_name] = model
                except Exception as e:
                    _LOGGER.warning("Failed to parse %s/%s: %s", locale_dir.name, filepath.name, e)
    
    return models


def _generate_definitions_file(models: Dict[str, Dict[str, Any]], output_dir: Path) -> None:
    """Generate the Python definitions module from parsed models."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sorted_models = dict(sorted(models.items()))
    models_json = json.dumps(sorted_models, indent=4, ensure_ascii=False, sort_keys=True)
    models_json = models_json.replace(': true', ': True').replace(': false', ': False').replace(': null', ': None')
    
    content = '"""Model definitions for Altherma heat pumps.\n\nAuto-generated from ESPAltherma. Do not edit.\n"""\n\nMODELS = '
    content += models_json + '\n'
    
    (output_dir / "__init__.py").write_text(content, encoding='utf-8')
    _LOGGER.info("Generated model definitions: %d models", len(models))
    for model_name in sorted(models.keys()):
        _LOGGER.info("  - %s", model_name)


def get_definitions_directory(component_dir: str) -> str:
    """Get the path to the definitions directory."""
    return os.path.join(component_dir, "definitions")


def _is_definitions_valid(definitions_dir: str) -> bool:
    """Check if definitions exist and are valid."""
    init_file = os.path.join(definitions_dir, "__init__.py")
    if not os.path.isfile(init_file):
        return False
    try:
        with open(init_file, 'r') as f:
            content = f.read()
        return 'MODELS' in content and len(content) > 1000
    except IOError:
        return False


def ensure_definitions(component_dir: str) -> None:
    """Ensure model definitions are generated from ESPAltherma.
    
    Args:
        component_dir: Path to the component directory.
        
    Raises:
        cv.Invalid: If definitions cannot be generated.
    """
    definitions_dir = get_definitions_directory(component_dir)
    
    if _is_definitions_valid(definitions_dir):
        return
    
    espaltherma_dir = get_espaltherma_directory(component_dir)
    
    if not os.path.isdir(espaltherma_dir):
        try:
            _clone_espaltherma_repository(espaltherma_dir)
        except ESPAlthermaCloneError as e:
            raise cv.Invalid(str(e)) from e
    
    try:
        _LOGGER.info("Generating model definitions from ESPAltherma...")
        models = _scan_definition_files(espaltherma_dir)
        if not models:
            raise cv.Invalid("No model definitions found in ESPAltherma")
        _generate_definitions_file(models, Path(definitions_dir))
    except cv.Invalid:
        raise
    except Exception as e:
        raise cv.Invalid(f"Failed to generate definitions: {e}") from e


def ensure_espaltherma(component_dir: str) -> None:
    """Ensure ESPAltherma is cloned and compatible.
    
    Checks if ESPAltherma exists in the expected location. If not, or if
    it's incompatible, clones the pinned version from GitHub.
    
    This function is called during configuration validation (lazy init)
    rather than at module import time.
    
    Args:
        component_dir: Path to the component directory.
    
    Raises:
        cv.Invalid: If ESPAltherma cannot be cloned or validated.
    """
    espaltherma_dir = get_espaltherma_directory(component_dir)
    
    # Check existing installation
    if os.path.isdir(espaltherma_dir):
        if _is_installation_valid(espaltherma_dir):
            return  # Valid installation found
        # Invalid installation - remove and re-clone
        _remove_directory_safe(espaltherma_dir)
    
    # Clone fresh copy
    try:
        _clone_espaltherma_repository(espaltherma_dir)
    except ESPAlthermaCloneError as e:
        raise cv.Invalid(str(e)) from e
