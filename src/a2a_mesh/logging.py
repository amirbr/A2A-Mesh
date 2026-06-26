"""Structured JSON logging setup."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with structured JSON-friendly format."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Module or component name (use __name__).

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(name)
