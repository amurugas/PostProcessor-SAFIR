"""
shared.database.base
~~~~~~~~~~~~~~~~~~~~
Abstract base class for all SAFIR SQLite database managers.

Concrete subclasses implement :meth:`create_tables` to set up the schema
appropriate for their analysis type (thermal, structural, …).
"""

import logging
import os
import sqlite3
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseDatabaseManager(ABC):
    """Manages a single SQLite database file for SAFIR post-processing.

    Parameters
    ----------
    db_path:
        Filesystem path to the ``.db`` file.  The file is created
        automatically if it does not exist.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.create_tables()
        self.create_views()

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        """Return an open :class:`sqlite3.Connection` with FK enforcement."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def create_tables(self) -> None:
        """Create all tables required by this analysis type.

        Implementations should be idempotent (use ``CREATE TABLE IF NOT
        EXISTS``) so that the method can be called safely on an existing
        database.
        """

    def create_views(self) -> None:
        """Create convenience views.  Override in subclasses as required."""

    def clear_database(self) -> None:
        """Prompt the user before wiping all rows from every table."""
        confirm = input("Are you sure you want to clear the database? (yes/no): ")
        if confirm.strip().lower() != "yes":
            logger.info("Database clearing aborted.")
            return
        self._do_clear()

    def _do_clear(self) -> None:  # pragma: no cover – subclasses override
        """Perform the actual DELETE operations (override in subclasses)."""
        raise NotImplementedError(
            "Subclasses must implement _do_clear() to list their tables."
        )

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    def define_sql_table(self, cursor: sqlite3.Cursor, sql_file: str) -> None:
        """Load a single table creation script from an SQL file."""
        sql_dir = "sql_tables"  # Directory containing the SQL files
        sql_path = os.path.join(sql_dir, sql_file)

        if not os.path.exists(sql_path):
            logger.error(f"SQL file not found: {sql_path}")
            return

        with open(sql_path, "r") as file:
            sql_script = file.read()
            cursor.executescript(sql_script)
            logger.info(f" SQL Tables created: {sql_file}")

    def define_sql_views(self, cursor: sqlite3.Cursor, sql_file: str) -> None:
        """Load a single table creation script from an SQL file."""
        sql_dir = "sql_views"  # Directory containing the SQL files
        sql_path = os.path.join(sql_dir, sql_file)

        if not os.path.exists(sql_path):
            logger.error(f"SQL file not found: {sql_path}")
            return

        with open(sql_path, "r") as file:
            sql_script = file.read()
            cursor.executescript(sql_script)
            logger.info(f" SQL Views created: {sql_file}")
    # ------------------------------------------------------------------
    # Shared table: timestamps
    # ------------------------------------------------------------------

    def insert_timestamp(self, time: float) -> int:
        """Insert *time* into the ``timestamps`` table (or ignore duplicate).

        Returns
        -------
        int
            The ``id`` of the inserted or existing row.
        """
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO timestamps (time) VALUES (?)", (time,)
            )
            cur.execute("SELECT id FROM timestamps WHERE time = ?", (time,))
            row = cur.fetchone()
            return row[0]
