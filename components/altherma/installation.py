"""ESPAltherma Installation Management.

This module handles cloning and validating the ESPAltherma repository
as a build-time dependency.
"""
from typing import List
import os
import subprocess
import logging
import shutil

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
