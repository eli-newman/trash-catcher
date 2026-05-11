"""Tests for configuration validation."""

import pytest
import config
from src.config_validator import validate_config, ConfigValidationError


def test_valid_config():
    """Default config should validate successfully."""
    # Should not raise
    validate_config()


def test_invalid_gravity():
    """Invalid gravity should raise ConfigValidationError."""
    # Save original
    original = config.GRAVITY_M_S2

    try:
        # Set invalid value
        config.GRAVITY_M_S2 = -5.0

        with pytest.raises(ConfigValidationError, match="GRAVITY_M_S2"):
            validate_config()
    finally:
        # Restore
        config.GRAVITY_M_S2 = original


def test_invalid_fov():
    """Invalid FOV should raise ConfigValidationError."""
    original = config.CAMERA_FOV_DEGREES

    try:
        config.CAMERA_FOV_DEGREES = 200  # Too large

        with pytest.raises(ConfigValidationError, match="CAMERA_FOV_DEGREES"):
            validate_config()
    finally:
        config.CAMERA_FOV_DEGREES = original


def test_invalid_fps():
    """Invalid FPS should raise ConfigValidationError."""
    original = config.CAMERA_FPS

    try:
        config.CAMERA_FPS = 0  # Zero FPS

        with pytest.raises(ConfigValidationError, match="CAMERA_FPS"):
            validate_config()
    finally:
        config.CAMERA_FPS = original


def test_min_greater_than_max_frames():
    """MIN_FRAMES > MAX_FRAMES should raise error."""
    orig_min = config.MIN_FRAMES_FOR_PREDICTION
    orig_max = config.MAX_FRAMES_FOR_PREDICTION

    try:
        config.MIN_FRAMES_FOR_PREDICTION = 20
        config.MAX_FRAMES_FOR_PREDICTION = 10

        with pytest.raises(ConfigValidationError, match="MIN_FRAMES_FOR_PREDICTION"):
            validate_config()
    finally:
        config.MIN_FRAMES_FOR_PREDICTION = orig_min
        config.MAX_FRAMES_FOR_PREDICTION = orig_max


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
