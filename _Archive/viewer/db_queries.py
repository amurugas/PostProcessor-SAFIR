"""
db_queries.py
~~~~~~~~~~~~~
All SQL queries for the SAFIR structural results viewer.

Every public function accepts a ``db_path`` string and returns a
:class:`pandas.DataFrame`.  SQL **must not** appear inside widget
callback code – use only these helpers there.

Actual schema (3-D structural SAFIR database)
----------------------------------------------
timestamps          id, time
beam_section        id, beam_tag, section
material_list       id, material_tag, material_name
shell_section       id, shell_tag, section
temperature_curve   id, time, temperature
model_data          id, name, value, description
node_coordinates    id, node_id, x, y, z
beam_fiber_strains  id, timestamp_id, beam_id, gauss_point, fiber_index, strain
beam_nodes          id, beam_id, N1, N2, N3, N4, beam_tag
rebar_strains       id, timestamp_id, shell_id, nga, rebar_id, eps_sx, eps_sy
shell_loads         id, load_id, shell_id, N1, N2, N3, P1, P2, P3, shell_tag
shell_nodes         id, shell_id, N1, N2, N3, N4, shell_tag
node_fixity         id, node_id, DOF1, DOF2, DOF3, DOF4, DOF5, DOF6, DOF7
node_displacements  id, timestamp_id, node_id, D1, D2, D3, D4, D5, D6, D7
reactions           id, timestamp_id, node_id, R1, R2, R3, R4, R5, R6, R7
beam_fiber_stresses id, timestamp_id, beam_id, gauss_point, fiber_index, stress
beam_forces         id, timestamp_id, beam_id, gauss_point, N, Mz, My, Mw, Mr2, Vz, Vy
shell_strains       id, timestamp_id, shell_id, integration_point, thickness,
                    Sx, Sy, Sz, Px, Py, Pz, Dx, Dy, Dz
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
    if not (_table_exists(db_path, "beam_nodes") and
            _table_exists(db_path, "beam_section")):
        return pd.DataFrame(columns=["beam_id", "section"])

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
    if not _table_exists(db_path, "node_coordinates"):
        return pd.DataFrame(columns=["node_id", "x", "y", "z"])

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
    if not (_table_exists(db_path, "beam_forces") and
            _table_exists(db_path, "timestamps")):
        return pd.DataFrame(columns=["time", "N", "Mz", "My", "Vz", "Vy"])

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
    if not (_table_exists(db_path, "node_displacements") and
            _table_exists(db_path, "timestamps")):
        return pd.DataFrame(columns=["time", "D1", "D2", "D3"])

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
