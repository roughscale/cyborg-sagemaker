"""Logging configuration for SageMaker training and evaluation."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    include_timestamp: bool = True
) -> None:
    """Configure logging for SageMaker environment.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        include_timestamp: Include timestamp in log messages
    """
    if format_string is None:
        if include_timestamp:
            format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        else:
            format_string = "[%(levelname)s] [%(name)s] %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True
    )

    # Set specific loggers to appropriate levels
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
