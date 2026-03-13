"""
db_queries_thermal.py
~~~~~~~~~~~~~~~~~~~~~
All SQL queries for the SAFIR 2-D thermal results viewer.

Every public function accepts a ``db_path`` string and returns a
:class:`pandas.DataFrame`.  SQL **must not** appear inside widget
callback code – use only these helpers there.

Assumed schema (2-D thermal SAFIR database)
-------------------------------------------
timestamps              id, time
thermal_nodes           node_id, section_id, x, y
thermal_elements        element_id, section_id
thermal_temperatures    timestamp_id, node_id, temperature
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

    Returns a DataFrame with at least a ``section_id`` column.
    Falls back gracefully if the expected table is absent.

    Columns: ``section_id``
    """
    if _table_exists(db_path, "thermal_nodes"):
        return _query(
            db_path,
            "SELECT DISTINCT section_id FROM thermal_nodes ORDER BY section_id",
        )
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
        Section / element group identifier.
    timestep_id:
        Primary key of the ``timestamps`` row.

    Columns: ``node_id``, ``x``, ``y``, ``temperature``
    """
    if not (_table_exists(db_path, "thermal_nodes") and
            _table_exists(db_path, "thermal_temperatures")):
        return pd.DataFrame(columns=["node_id", "x", "y", "temperature"])

    return _query(
        db_path,
        """
        SELECT  tn.node_id,
                tn.x,
                tn.y,
                tt.temperature
        FROM    thermal_nodes tn
        JOIN    thermal_temperatures tt ON tt.node_id = tn.node_id
        WHERE   tn.section_id   = ?
          AND   tt.timestamp_id = ?
        ORDER   BY tn.node_id
        """,
        (section_id, timestep_id),
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
        Section / element group identifier (used to validate node membership).
    node_id:
        Node identifier.

    Columns: ``time``, ``temperature``
    """
    if not (_table_exists(db_path, "timestamps") and
            _table_exists(db_path, "thermal_temperatures")):
        return pd.DataFrame(columns=["time", "temperature"])

    return _query(
        db_path,
        """
        SELECT  ts.time,
                tt.temperature
        FROM    thermal_temperatures tt
        JOIN    timestamps ts ON ts.id = tt.timestamp_id
        JOIN    thermal_nodes tn  ON tn.node_id = tt.node_id
        WHERE   tt.node_id  = ?
          AND   tn.section_id = ?
        ORDER   BY ts.time
        """,
        (node_id, section_id),
    )


def get_node_list_for_section(db_path: str, section_id: int | str) -> pd.DataFrame:
    """Return all node IDs and coordinates for a given section.

    Columns: ``node_id``, ``x``, ``y``
    """
    if not _table_exists(db_path, "thermal_nodes"):
        return pd.DataFrame(columns=["node_id", "x", "y"])

    return _query(
        db_path,
        """
        SELECT node_id, x, y
        FROM   thermal_nodes
        WHERE  section_id = ?
        ORDER  BY node_id
        """,
        (section_id,),
    )
