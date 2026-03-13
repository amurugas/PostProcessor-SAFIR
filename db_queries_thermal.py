"""
db_queries_thermal.py
~~~~~~~~~~~~~~~~~~~~~
All SQL queries for the SAFIR 2-D thermal results viewer.

Every public function accepts a ``db_path`` string and returns a
:class:`pandas.DataFrame`.  SQL **must not** appear inside widget
callback code – use only these helpers there.

Actual schema (2-D thermal SAFIR database)
-------------------------------------------
timestamps              id, time
node_coordinates        node_id, x, y
node_temperatures       timestamp_id, node_id, Temperature
"""

from __future__ import annotations

import sqlite3

import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _query(db_path: str, sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = _connect(db_path)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def _table_exists(db_path: str, name: str) -> bool:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
            (name,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _list_tables(db_path: str) -> list[str]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------


def get_thermal_sections(db_path: str) -> pd.DataFrame:
    """Return distinct section IDs available in the thermal database.

    Since the actual schema does not have a ``section_id`` column, a single
    default section (id = 1) is returned whenever ``node_coordinates`` exists
    and contains at least one row.

    Returns a DataFrame with a ``section_id`` column.
    Falls back gracefully if the expected table is absent.

    Columns: ``section_id``
    """
    if _table_exists(db_path, "node_coordinates"):
        result = _query(db_path, "SELECT COUNT(*) as cnt FROM node_coordinates")
        if not result.empty and result.iloc[0]["cnt"] > 0:
            return pd.DataFrame({"section_id": [1]})
    # Fallback: return empty frame so the UI can handle it cleanly
    return pd.DataFrame(columns=["section_id"])


def get_thermal_timesteps(db_path: str) -> pd.DataFrame:
    """Return all available time steps.

    Columns: ``id``, ``time``
    """
    if _table_exists(db_path, "timestamps"):
        return _query(db_path, "SELECT id, time FROM timestamps ORDER BY time")
    return pd.DataFrame(columns=["id", "time"])


def get_temperature_grid(
    db_path: str,
    section_id: int | str,
    timestep_id: int,
) -> pd.DataFrame:
    """Return the 2-D temperature field for one section at one time step.

    Parameters
    ----------
    section_id:
        Section / element group identifier (unused in this schema, kept for
        API compatibility).
    timestep_id:
        Primary key of the ``timestamps`` row.

    Columns: ``node_id``, ``x``, ``y``, ``temperature``
    """
    if not (_table_exists(db_path, "node_coordinates") and
            _table_exists(db_path, "node_temperatures")):
        return pd.DataFrame(columns=["node_id", "x", "y", "temperature"])

    return _query(
        db_path,
        """
        SELECT  nc.node_id,
                nc.x,
                nc.y,
                nt.Temperature as temperature
        FROM    node_coordinates nc
        JOIN    node_temperatures nt ON nt.node_id = nc.node_id
        WHERE   nt.timestamp_id = ?
        ORDER   BY nc.node_id
        """,
        (timestep_id,),
    )


def get_temperature_history(
    db_path: str,
    section_id: int | str,
    node_id: int,
) -> pd.DataFrame:
    """Return temperature vs time for a single node inside a section.

    Parameters
    ----------
    section_id:
        Section / element group identifier (unused in this schema, kept for
        API compatibility).
    node_id:
        Node identifier.

    Columns: ``time``, ``temperature``
    """
    if not (_table_exists(db_path, "timestamps") and
            _table_exists(db_path, "node_temperatures")):
        return pd.DataFrame(columns=["time", "temperature"])

    return _query(
        db_path,
        """
        SELECT  ts.time,
                nt.Temperature as temperature
        FROM    node_temperatures nt
        JOIN    timestamps ts ON ts.id = nt.timestamp_id
        WHERE   nt.node_id = ?
        ORDER   BY ts.time
        """,
        (node_id,),
    )


def get_node_list_for_section(db_path: str, section_id: int | str) -> pd.DataFrame:
    """Return all node IDs and coordinates for a given section.

    Parameters
    ----------
    section_id:
        Section identifier (unused in this schema, kept for API compatibility).

    Columns: ``node_id``, ``x``, ``y``
    """
    if not _table_exists(db_path, "node_coordinates"):
        return pd.DataFrame(columns=["node_id", "x", "y"])

    return _query(
        db_path,
        """
        SELECT node_id, x, y
        FROM   node_coordinates
        ORDER  BY node_id
        """,
    )
