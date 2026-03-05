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
            self._create_common_tables(cur)
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS node_coordinates (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL,
                    x       REAL,
                    y       REAL
                );

                CREATE TABLE IF NOT EXISTS solid_mesh (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    solid_id     INTEGER NOT NULL,
                    N1           INTEGER,
                    N2           INTEGER,
                    N3           INTEGER,
                    N4           INTEGER,
                    material_tag INTEGER
                );

                CREATE TABLE IF NOT EXISTS material_list (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_tag  INTEGER NOT NULL,
                    material_name TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS node_temperatures (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_id INTEGER NOT NULL,
                    node_id      INTEGER NOT NULL,
                    Temperature  REAL
                );

                CREATE TABLE IF NOT EXISTS max_temp_by_material (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_tag  INTEGER NOT NULL,
                    material_name TEXT,
                    timestamp_id  INTEGER NOT NULL,
                    max_temp      REAL
                );
            """)
            logger.info("Thermal database tables ensured.")

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def _do_clear(self) -> None:
        tables = [
            "node_temperatures",
            "max_temp_by_material",
            "node_coordinates",
            "solid_mesh",
            "material_list",
            "timestamps",
            "temperature_curve",
            "model_data",
        ]
        with self.connect() as conn:
            cur = conn.cursor()
            for table in tables:
                cur.execute(f"DELETE FROM {table}")
        logger.info("Thermal database cleared.")
