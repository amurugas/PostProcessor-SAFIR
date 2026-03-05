"""
shared.utils.config
~~~~~~~~~~~~~~~~~~~
Central configuration management for PostProcessor-SAFIR.

Settings are read from environment variables (or a ``.env`` file when
`python-dotenv` is installed) and can be overridden programmatically.

Usage::

    from shared.utils.config import Config

    cfg = Config()
    print(cfg.log_level)   # "INFO"
    print(cfg.db_dir)      # path from DB_DIR env-var or "."
"""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Application-wide configuration container.

    All attributes can be overridden by environment variables of the same
    name (upper-cased).  Defaults are sensible for local development.
    """

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    log_format: str = field(
        default_factory=lambda: os.getenv(
            "LOG_FORMAT",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    )

    # Paths
    db_dir: str = field(
        default_factory=lambda: os.getenv("DB_DIR", ".")
    )
    data_dir: str = field(
        default_factory=lambda: os.getenv("DATA_DIR", "data")
    )
    output_dir: str = field(
        default_factory=lambda: os.getenv("OUTPUT_DIR", "output")
    )

    # Analysis defaults
    default_analysis_type: str = field(
        default_factory=lambda: os.getenv("DEFAULT_ANALYSIS_TYPE", "structural")
    )

    def as_dict(self) -> dict:
        """Return configuration as a plain dictionary."""
        return {
            "log_level": self.log_level,
            "log_format": self.log_format,
            "db_dir": self.db_dir,
            "data_dir": self.data_dir,
            "output_dir": self.output_dir,
            "default_analysis_type": self.default_analysis_type,
        }
