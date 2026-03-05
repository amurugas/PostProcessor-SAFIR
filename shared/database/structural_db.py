"""
shared.database.structural_db
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Database manager for 3D structural analysis results.

Schema mirrors the tables created by
``3D-STRUCTURAL/2_3D-Struct-Create-DB/Create_DB_from_XML.py``.
"""

import logging
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
            self._create_common_tables(cur)
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS node_coordinates (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL,
                    x       REAL,
                    y       REAL,
                    z       REAL
                );

                CREATE TABLE IF NOT EXISTS beam_nodes (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    beam_id  INTEGER NOT NULL,
                    N1       REAL,
                    N3       REAL,
                    N2       REAL,
                    N4       REAL,
                    beam_tag REAL
                );

                CREATE TABLE IF NOT EXISTS shell_nodes (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    shell_id  INTEGER NOT NULL,
                    N1        REAL,
                    N2        REAL,
                    N3        REAL,
                    N4        REAL,
                    shell_tag REAL
                );

                CREATE TABLE IF NOT EXISTS node_fixity (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL,
                    DOF1    TEXT DEFAULT 'NO',
                    DOF2    TEXT DEFAULT 'NO',
                    DOF3    TEXT DEFAULT 'NO',
                    DOF4    TEXT DEFAULT 'NO',
                    DOF5    TEXT DEFAULT 'NO',
                    DOF6    TEXT DEFAULT 'NO',
                    DOF7    TEXT DEFAULT 'NO'
                );

                CREATE TABLE IF NOT EXISTS beam_section (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    beam_tag INTEGER NOT NULL,
                    section  TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS shell_section (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    shell_tag INTEGER NOT NULL,
                    section   TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS shell_loads (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    load_id  INTEGER NOT NULL,
                    load_fct TEXT,
                    shell_id INTEGER NOT NULL,
                    P1       REAL,
                    P2       REAL,
                    P3       REAL
                );

                CREATE TABLE IF NOT EXISTS material_list (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_tag  INTEGER NOT NULL,
                    material_name TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS node_displacements (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_id INTEGER NOT NULL,
                    node_id      INTEGER NOT NULL,
                    D1           REAL DEFAULT 0,
                    D2           REAL DEFAULT 0,
                    D3           REAL DEFAULT 0,
                    D4           REAL DEFAULT 0,
                    D5           REAL DEFAULT 0,
                    D6           REAL DEFAULT 0,
                    D7           REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS beam_forces (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_id  INTEGER NOT NULL,
                    beam_id       INTEGER NOT NULL,
                    gauss_point   INTEGER NOT NULL,
                    N             REAL,
                    Mz            REAL,
                    My            REAL,
                    Mw            REAL,
                    Mr2           REAL,
                    Vz            REAL,
                    Vy            REAL
                );

                CREATE TABLE IF NOT EXISTS shell_strains (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_id      INTEGER NOT NULL,
                    shell_id          INTEGER NOT NULL,
                    integration_point INTEGER,
                    thickness         INTEGER,
                    Sx                REAL,
                    Sy                REAL,
                    Sz                REAL,
                    Px                REAL,
                    Py                REAL,
                    Pz                REAL,
                    Dx                REAL,
                    Dy                REAL,
                    Dz                REAL
                );

                CREATE TABLE IF NOT EXISTS rebar_strains (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_id INTEGER NOT NULL,
                    shell_id     INTEGER NOT NULL,
                    nga          INTEGER NOT NULL,
                    rebar_id     INTEGER NOT NULL,
                    eps_sx       REAL,
                    eps_sy       REAL
                );

                CREATE TABLE IF NOT EXISTS reactions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_id INTEGER NOT NULL,
                    node_id      INTEGER NOT NULL,
                    R1           REAL DEFAULT 0,
                    R2           REAL DEFAULT 0,
                    R3           REAL DEFAULT 0,
                    R4           REAL DEFAULT 0,
                    R5           REAL DEFAULT 0,
                    R6           REAL DEFAULT 0,
                    R7           REAL DEFAULT 0
                );
            """)
            logger.info("Structural database tables ensured.")

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def create_views(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.executescript("""
                DROP VIEW IF EXISTS beam_section_lookup;
                CREATE VIEW beam_section_lookup AS
                    SELECT bn.beam_id, bs.section
                    FROM   beam_nodes bn
                    JOIN   beam_section bs ON bn.beam_tag = bs.beam_tag;

                DROP VIEW IF EXISTS shell_section_lookup;
                CREATE VIEW shell_section_lookup AS
                    SELECT sn.shell_id, ss.section
                    FROM   shell_nodes sn
                    JOIN   shell_section ss ON sn.shell_tag = ss.shell_tag;
            """)
            logger.info("Structural views created.")

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def _do_clear(self) -> None:
        tables = [
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
        with self.connect() as conn:
            cur = conn.cursor()
            for table in tables:
                cur.execute(f"DELETE FROM {table}")
        logger.info("Structural database cleared.")
