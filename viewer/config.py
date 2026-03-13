"""
config.py
~~~~~~~~~
Paths and configuration for the SAFIR structural results viewer.

Override the database path via the environment variable ``SAFIR_DB_PATH``
or by passing ``--args --db <path>`` on the Bokeh CLI.
"""

import os

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Path to the SAFIR SQLite structural results database.
# Set SAFIR_DB_PATH environment variable or pass --args --db <path> to Bokeh.
DB_PATH: str = os.environ.get("SAFIR_DB_PATH", "Raw.db")

# ---------------------------------------------------------------------------
# Query defaults
# ---------------------------------------------------------------------------

# Gauss point used for beam-force and fiber queries (1 = first, typical choice).
DEFAULT_GAUSS_POINT: int = 1

# ---------------------------------------------------------------------------
# Server (informational – the actual values are passed to `bokeh serve`)
# ---------------------------------------------------------------------------

PORT: int = 5006
