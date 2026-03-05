"""
shared.database.base
~~~~~~~~~~~~~~~~~~~~
Abstract base class for all SAFIR SQLite database managers.

Concrete subclasses implement :meth:`create_tables` to set up the schema
appropriate for their analysis type (thermal, structural, …).
"""

import logging
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

    # ------------------------------------------------------------------
    # Shared table: timestamps
    # ------------------------------------------------------------------

    def _create_common_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create tables that are common across analysis types."""
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS timestamps (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                time REAL    NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS model_data (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS temperature_curve (
                id          INTEGER PRIMARY KEY,
                time        REAL,
                temperature REAL
            );
        """)

    # ------------------------------------------------------------------
    # Shared utilities
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

    def create_views(self) -> None:
        """Create convenience views.  Override in subclasses as required."""
