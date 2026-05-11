"""
Logging configuration for trash-catcher system.

Sets up structured logging for production use with appropriate levels
for different components.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> None:
    """
    Configure logging for the entire application.

    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR")
        log_file: Optional path to log file
        log_to_console: Whether to log to console (stdout/stderr)

    Usage:
        from src.logging_config import setup_logging
        setup_logging(level="INFO", log_file="trash_catcher.log")
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    # Format: [2024-01-19 14:32:15,123] INFO [predictor] Prediction computed in 2.3ms: ...
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (stdout for INFO/DEBUG, stderr for WARNING/ERROR)
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.info(f"Logging to file: {log_file}")

    # Set module-specific log levels
    # Predictor is chatty at INFO level, so keep at INFO
    logging.getLogger('src.predictor').setLevel(numeric_level)

    # Simulator can be DEBUG when needed
    logging.getLogger('src.simulator').setLevel(max(numeric_level, logging.INFO))

    # Matplotlib is very noisy, keep it quiet
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    root_logger.info(f"Logging initialized at {level} level")


def setup_hardware_logging(log_dir: str = "./logs") -> None:
    """
    Configure logging for hardware deployment.

    Creates timestamped log files for each run and keeps console output minimal.

    Args:
        log_dir: Directory to store log files
    """
    from datetime import datetime

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"trash_catcher_{timestamp}.log"

    # Setup logging with file output
    setup_logging(
        level="INFO",
        log_file=str(log_file),
        log_to_console=True  # Still show important messages on console
    )

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Trash Catcher System Starting")
    logger.info(f"Log file: {log_file}")
    logger.info("="*60)


def setup_debug_logging() -> None:
    """
    Configure verbose logging for debugging.

    Use this during development to see all internal details.
    """
    setup_logging(level="DEBUG", log_to_console=True)

    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled - very verbose output")
