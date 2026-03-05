"""
shared.utils.logger
~~~~~~~~~~~~~~~~~~~
Centralised logging configuration for PostProcessor-SAFIR.

Usage::

    from shared.utils.logger import setup_logger

    logger = setup_logger(__name__)
    logger.info("Processing started.")
"""

import logging
import os


def setup_logger(
    name: str,
    level: str | None = None,
    fmt: str | None = None,
) -> logging.Logger:
    """Return a configured :class:`logging.Logger`.

    Parameters
    ----------
    name:
        Logger name – typically ``__name__`` of the calling module.
    level:
        Logging level string (e.g. ``"DEBUG"``, ``"INFO"``).  Falls back
        to the ``LOG_LEVEL`` environment variable or ``"INFO"``.
    fmt:
        Log message format string.  Falls back to the ``LOG_FORMAT``
        environment variable or a sensible default.

    Returns
    -------
    logging.Logger
    """
    effective_level = (
        level
        or os.getenv("LOG_LEVEL", "INFO")
    ).upper()

    effective_fmt = fmt or os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(effective_fmt))
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, effective_level, logging.INFO))
    return logger
