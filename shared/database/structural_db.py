"""
shared.database.structural_db
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Database manager for 3D structural analysis results.

Schema mirrors the tables created by
``3D-STRUCTURAL/2_3D-Struct-Create-DB/Create_DB_from_XML.py``.
"""

import logging
import os.path
import sqlite3

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class StructuralDatabaseManager(BaseDatabaseManager):
    """SQLite database manager for 3D-STRUCTURAL SAFIR results."""

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            self.define_sql_table(cur, "3D-Struct.sql")

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def create_views(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            self.define_sql_views(cur, "3D-Struct-views.sql")


    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def _do_clear(self) -> None:
        tables = [
            "beam_fiber_strains",
            "beam_fiber_stresses",
            "node_displacements",
            "beam_forces",
            "shell_strains",
            "rebar_strains",
            "reactions",
            "node_coordinates",
            "beam_nodes",
            "shell_nodes",
            "node_fixity",
            "beam_section",
            "shell_section",
            "shell_loads",
            "material_list",
            "timestamps",
            "temperature_curve",
            "model_data",
        ]

        views = [
            "beam_section_lookup",
            "shell_section_lookup",
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
