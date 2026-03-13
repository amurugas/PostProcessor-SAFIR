"""
db_queries.py
~~~~~~~~~~~~~
All SQL queries for the SAFIR structural results viewer.

Every public function accepts a ``db_path`` string and returns a
:class:`pandas.DataFrame`.  SQL **must not** appear inside widget
callback code – use only these helpers there.

Assumed schema (3-D structural SAFIR database)
----------------------------------------------
timestamps          id, time
node_coordinates    node_id, x, y, z
beam_nodes          beam_id, beam_tag, N1, N2, N3, N4
beam_section        beam_tag, section
node_displacements  timestamp_id, node_id, D1, D2, D3, D4, D5, D6, D7
beam_forces         timestamp_id, beam_id, gauss_point, N, Mz, My, Vz, Vy
beam_fiber_stresses timestamp_id, beam_id, gauss_point, fiber_index, stress
beam_fiber_strains  timestamp_id, beam_id, gauss_point, fiber_index, strain
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


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------


def get_beam_list(db_path: str) -> pd.DataFrame:
    """Return all beams with their section label.

    Columns: ``beam_id``, ``section``
    """
    return _query(
        db_path,
        """
        SELECT DISTINCT bn.beam_id,
               COALESCE(bs.section, 'N/A') AS section
        FROM   beam_nodes bn
        LEFT JOIN beam_section bs ON bn.beam_tag = bs.beam_tag
        ORDER  BY bn.beam_id
        """,
    )


def get_node_list(db_path: str) -> pd.DataFrame:
    """Return all nodes with their coordinates.

    Columns: ``node_id``, ``x``, ``y``, ``z``
    """
    return _query(
        db_path,
        "SELECT node_id, x, y, z FROM node_coordinates ORDER BY node_id",
    )


def get_beam_force_history(
    db_path: str,
    beam_id: int,
    gauss_point: int = 1,
) -> pd.DataFrame:
    """Return beam internal-force history for one beam / Gauss point.

    Columns: ``time``, ``N``, ``Mz``, ``My``, ``Vz``, ``Vy``
    """
    return _query(
        db_path,
        """
        SELECT ts.time, bf.N, bf.Mz, bf.My, bf.Vz, bf.Vy
        FROM   beam_forces bf
        JOIN   timestamps ts ON bf.timestamp_id = ts.id
        WHERE  bf.beam_id    = ?
          AND  bf.gauss_point = ?
        ORDER  BY ts.time
        """,
        (beam_id, gauss_point),
    )


def get_node_displacement_history(db_path: str, node_id: int) -> pd.DataFrame:
    """Return displacement time-history for one node.

    Columns: ``time``, ``D1``, ``D2``, ``D3``
    """
    return _query(
        db_path,
        """
        SELECT ts.time, nd.D1, nd.D2, nd.D3
        FROM   node_displacements nd
        JOIN   timestamps ts ON nd.timestamp_id = ts.id
        WHERE  nd.node_id = ?
        ORDER  BY ts.time
        """,
        (node_id,),
    )


def get_fiber_data(
    db_path: str,
    beam_id: int,
    gauss_point: int = 1,
    fiber_type: str = "stress",
) -> pd.DataFrame:
    """Return fiber result history for one beam / Gauss point.

    Parameters
    ----------
    fiber_type:
        ``'stress'`` queries ``beam_fiber_stresses`` (column ``stress``);
        ``'strain'`` queries ``beam_fiber_strains`` (column ``strain``).

    Columns: ``time``, ``fiber_index``, ``value``
    """
    if fiber_type == "strain":
        table = "beam_fiber_strains"
        value_col = "strain"
    else:
        table = "beam_fiber_stresses"
        value_col = "stress"

    if not _table_exists(db_path, table):
        return pd.DataFrame(columns=["time", "fiber_index", "value"])

    return _query(
        db_path,
        f"""
        SELECT ts.time, bf.fiber_index, bf.{value_col} AS value
        FROM   {table} bf
        JOIN   timestamps ts ON bf.timestamp_id = ts.id
        WHERE  bf.beam_id    = ?
          AND  bf.gauss_point = ?
        ORDER  BY ts.time, bf.fiber_index
        """,
        (beam_id, gauss_point),
    )
