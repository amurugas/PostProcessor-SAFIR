"""
SAFIR-Dashboard Bokeh Application
==================================
A Bokeh server app that visualises SAFIR thermal analysis results stored
in an SQLite database.

Entry points
------------
- :mod:`main`   – Bokeh document (pass to ``bokeh serve``)
- :mod:`server` – CLI launcher with temporary-cache lifecycle management
"""

from .server import main
from .cache_db import CacheDatabase

__all__ = [
    "main",
    "CacheDatabase",
]