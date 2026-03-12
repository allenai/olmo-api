"""Logging configuration for evaluations."""

import logging
import sys

# Create logger
logger = logging.getLogger("evaluations")


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging with a standard format.

    Args:
        level: Logging level (default: INFO)
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(level)


setup_logging()
