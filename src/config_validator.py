"""
Configuration validation module.

Validates all config parameters at startup to catch invalid settings
before they cause runtime errors.
"""

import logging
import config

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration is invalid."""
    pass


def validate_config() -> None:
    """
    Validate all configuration parameters.

    Raises:
        ConfigValidationError: if any parameter is invalid

    Call this at program startup:
        from src.config_validator import validate_config
        validate_config()
    """
    errors = []

    # Physics parameters
    if not (0 < config.GRAVITY_M_S2 < 15):
        errors.append(f"GRAVITY_M_S2 must be 0-15, got {config.GRAVITY_M_S2}")

    # Camera parameters
    if not (1 <= config.CAMERA_FOV_DEGREES <= 180):
        errors.append(f"CAMERA_FOV_DEGREES must be 1-180, got {config.CAMERA_FOV_DEGREES}")

    if not (0.1 <= config.CAMERA_MAX_RANGE_M <= 100):
        errors.append(f"CAMERA_MAX_RANGE_M must be 0.1-100, got {config.CAMERA_MAX_RANGE_M}")

    if not (1 <= config.CAMERA_FPS <= 240):
        errors.append(f"CAMERA_FPS must be 1-240, got {config.CAMERA_FPS}")

    if not isinstance(config.CAMERA_RESOLUTION, tuple) or len(config.CAMERA_RESOLUTION) != 2:
        errors.append(f"CAMERA_RESOLUTION must be (width, height) tuple, got {config.CAMERA_RESOLUTION}")
    elif not (config.CAMERA_RESOLUTION[0] > 0 and config.CAMERA_RESOLUTION[1] > 0):
        errors.append(f"CAMERA_RESOLUTION dimensions must be positive, got {config.CAMERA_RESOLUTION}")

    if not (0 <= config.CAMERA_DEPTH_NOISE_M <= 0.5):
        errors.append(f"CAMERA_DEPTH_NOISE_M must be 0-0.5, got {config.CAMERA_DEPTH_NOISE_M}")

    # Camera position
    if not isinstance(config.CAMERA_POSITION, tuple) or len(config.CAMERA_POSITION) != 3:
        errors.append(f"CAMERA_POSITION must be (x, y, z) tuple, got {config.CAMERA_POSITION}")
    elif not all(abs(v) < 100 for v in config.CAMERA_POSITION):
        errors.append(f"CAMERA_POSITION coordinates must be < 100m, got {config.CAMERA_POSITION}")

    # Catch plane
    if not (-10 <= config.CATCH_PLANE_HEIGHT_M <= 10):
        errors.append(f"CATCH_PLANE_HEIGHT_M must be -10 to 10, got {config.CATCH_PLANE_HEIGHT_M}")

    # Prediction parameters
    if not (2 <= config.MIN_FRAMES_FOR_PREDICTION <= 20):
        errors.append(f"MIN_FRAMES_FOR_PREDICTION must be 2-20, got {config.MIN_FRAMES_FOR_PREDICTION}")

    if not (5 <= config.MAX_FRAMES_FOR_PREDICTION <= 100):
        errors.append(f"MAX_FRAMES_FOR_PREDICTION must be 5-100, got {config.MAX_FRAMES_FOR_PREDICTION}")

    if config.MIN_FRAMES_FOR_PREDICTION > config.MAX_FRAMES_FOR_PREDICTION:
        errors.append(
            f"MIN_FRAMES_FOR_PREDICTION ({config.MIN_FRAMES_FOR_PREDICTION}) "
            f"must be <= MAX_FRAMES_FOR_PREDICTION ({config.MAX_FRAMES_FOR_PREDICTION})"
        )

    # Simulation defaults (optional, only used in simulator)
    if hasattr(config, 'DEFAULT_THROW_HEIGHT_M'):
        if not (0.1 <= config.DEFAULT_THROW_HEIGHT_M <= 50):
            errors.append(f"DEFAULT_THROW_HEIGHT_M must be 0.1-50, got {config.DEFAULT_THROW_HEIGHT_M}")

    if hasattr(config, 'DEFAULT_THROW_VELOCITY_M_S'):
        if not (0.1 <= config.DEFAULT_THROW_VELOCITY_M_S <= 50):
            errors.append(f"DEFAULT_THROW_VELOCITY_M_S must be 0.1-50, got {config.DEFAULT_THROW_VELOCITY_M_S}")

    # Cross-parameter validation
    # Warn if catch plane is very high relative to typical throws
    if hasattr(config, 'DEFAULT_THROW_HEIGHT_M'):
        if config.CATCH_PLANE_HEIGHT_M > config.DEFAULT_THROW_HEIGHT_M * 0.8:
            logger.warning(
                f"CATCH_PLANE_HEIGHT_M ({config.CATCH_PLANE_HEIGHT_M}m) is very high "
                f"relative to DEFAULT_THROW_HEIGHT_M ({config.DEFAULT_THROW_HEIGHT_M}m). "
                f"Objects may not reach catch plane."
            )

    # Warn if FOV is very narrow (might miss objects)
    if config.CAMERA_FOV_DEGREES < 30:
        logger.warning(
            f"CAMERA_FOV_DEGREES ({config.CAMERA_FOV_DEGREES}°) is very narrow. "
            f"May miss objects entering from sides."
        )

    # Warn if FPS is low (affects prediction latency)
    if config.CAMERA_FPS < 20:
        logger.warning(
            f"CAMERA_FPS ({config.CAMERA_FPS}) is low. "
            f"May need more time to accumulate MIN_FRAMES_FOR_PREDICTION frames."
        )

    # Calculate time to first prediction (only if FPS is valid)
    if config.CAMERA_FPS > 0:
        time_to_first_prediction = config.MIN_FRAMES_FOR_PREDICTION / config.CAMERA_FPS
        if time_to_first_prediction > 0.5:
            logger.warning(
                f"Time to first prediction is {time_to_first_prediction:.2f}s "
                f"({config.MIN_FRAMES_FOR_PREDICTION} frames at {config.CAMERA_FPS} FPS). "
                f"Consider increasing FPS or decreasing MIN_FRAMES_FOR_PREDICTION."
            )
    else:
        time_to_first_prediction = float('inf')

    # If any errors, raise exception
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise ConfigValidationError(error_msg)

    logger.info("Configuration validation passed")
    logger.info(f"  Camera: {config.CAMERA_FOV_DEGREES}° FOV, {config.CAMERA_FPS} FPS, {config.CAMERA_MAX_RANGE_M}m range")
    logger.info(f"  Catch plane: {config.CATCH_PLANE_HEIGHT_M}m")
    logger.info(f"  Prediction: {config.MIN_FRAMES_FOR_PREDICTION}-{config.MAX_FRAMES_FOR_PREDICTION} frames")
    logger.info(f"  Time to first prediction: {time_to_first_prediction:.3f}s")
