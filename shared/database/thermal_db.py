"""
shared.database.thermal_db
~~~~~~~~~~~~~~~~~~~~~~~~~~
Database manager for 2D thermal analysis results.

Schema mirrors the tables created by
``2D-THERMAL/2_2D-Thermal-Create-DB/2D-Thermal-CreateDB.py``.
"""

import logging
import sqlite3

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class ThermalDatabaseManager(BaseDatabaseManager):
    """SQLite database manager for 2D-THERMAL SAFIR results."""

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            self.define_sql_table(cur, "2D-Thermal.sql")

    def create_views(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            self.define_sql_views(cur, "2D-Thermal-views.sql")
    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def _do_clear(self) -> None:
        tables = [
            "frontiers",
            "node_temperatures",
            "node_coordinates",
            "solid_mesh",
            "material_list",
            "timestamps",
            "temperature_curve",
            "model_data",
        ]
        views = [
            "solid_avg_temperature",
         ]

        with self.connect() as conn:
            cur = conn.cursor()
            for table in tables:
                cur.execute(f"DELETE FROM {table}")
                cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

            for view in views:
                cur.execute(f"DROP VIEW IF EXISTS {view}")

        logger.info("Tables and views cleared.")
