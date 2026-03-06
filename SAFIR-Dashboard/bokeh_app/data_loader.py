"""
SAFIR-Dashboard · bokeh_app.data_loader
=========================================
All SQLite queries are executed against the **cache database** (the temporary
copy built by :class:`~bokeh_app.cache_db.CacheDatabase`).  Every public
method returns a :class:`pandas.DataFrame`.

Usage example::

    loader = DataLoader("/tmp/safir_cache_xyz.db")
    time_df  = loader.get_time_steps()
    temps_df = loader.get_section_temperatures(timestamp_id=5)
"""

from __future__ import annotations

import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)


class DataLoader:
    """Query helper for the SAFIR cache database.

    Parameters
    ----------
    cache_path:
        Filesystem path to the temporary SQLite cache database.
    """

    def __init__(self, cache_path: str) -> None:
        self._path = cache_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.execute("PRAGMA query_only = ON")
        return conn

    def _query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        conn = self._connect()
        try:
            return pd.read_sql_query(sql, conn, params=params)
        finally:
            conn.close()

    def _table_exists(self, name: str) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
                (name,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_time_steps(self) -> pd.DataFrame:
        """Return all timestamps ordered by time.

        Columns: ``id``, ``time``
        """
        return self._query("SELECT id, time FROM timestamps ORDER BY time")

    def get_node_coordinates(self) -> pd.DataFrame:
        """Return all node coordinates.

        Columns: ``node_id``, ``x``, ``y``
        """
        return self._query("SELECT node_id, x, y FROM node_coordinates")

    def get_solid_mesh(self) -> pd.DataFrame:
        """Return solid-mesh connectivity.

        Columns: ``solid_id``, ``N1``, ``N2``, ``N3``, ``N4``, ``material_tag``
        """
        return self._query(
            "SELECT solid_id, N1, N2, N3, N4, material_tag FROM solid_mesh"
        )

    def get_material_lookup(self) -> pd.DataFrame:
        """Return material tag → name mapping.

        Columns: ``material_tag``, ``material_name``

        Returns an empty DataFrame when the ``material_list`` table is absent.
        """
        if not self._table_exists("material_list"):
            return pd.DataFrame(columns=["material_tag", "material_name"])
        return self._query("SELECT material_tag, material_name FROM material_list")

    def get_frontiers(self) -> pd.DataFrame:
        """Return frontier (boundary-condition) data.

        Columns: ``solid_id``, ``face1``, ``face2``, ``face3``, ``face4``

        Returns an empty DataFrame when the ``frontiers`` table is absent.
        """
        if not self._table_exists("frontiers"):
            return pd.DataFrame(columns=["solid_id", "face1", "face2", "face3", "face4"])
        return self._query(
            "SELECT solid_id, face1, face2, face3, face4 FROM frontiers"
        )

    def get_section_temperatures(self, timestamp_id: int) -> pd.DataFrame:
        """Return node temperatures for a single timestep.

        Parameters
        ----------
        timestamp_id:
            The ``id`` value from the ``timestamps`` table.

        Columns: ``node_id``, ``Temperature``
        """
        return self._query(
            "SELECT node_id, Temperature FROM node_temperatures WHERE timestamp_id = ?",
            (timestamp_id,),
        )

    def get_node_history(self, node_id: int) -> pd.DataFrame:
        """Return the temperature history of a single node.

        Parameters
        ----------
        node_id:
            Node identifier.

        Columns: ``time``, ``Temperature``
        """
        return self._query(
            """
            SELECT ts.time, nt.Temperature
            FROM node_temperatures nt
            JOIN timestamps ts ON ts.id = nt.timestamp_id
            WHERE nt.node_id = ?
            ORDER BY ts.time
            """,
            (node_id,),
        )

    def get_material_summary(self) -> pd.DataFrame:
        """Return per-material average and maximum temperature across time.

        Uses the pre-built ``vw_material_temperature_summary`` view when
        available, falling back to an inline CTE otherwise.

        Columns: ``material_id``, ``material_section_lookup``, ``timestep``,
        ``avg_temp_material``, ``max_temp_material``
        """
        if self._table_exists("vw_material_temperature_summary"):
            return self._query(
                "SELECT * FROM vw_material_temperature_summary ORDER BY timestep, material_id"
            )

        return self._query(
            """
            WITH solid_nodes AS (
                SELECT solid_id, material_tag, N1 AS node_id FROM solid_mesh
                UNION ALL
                SELECT solid_id, material_tag, N2 AS node_id FROM solid_mesh
                UNION ALL
                SELECT solid_id, material_tag, N3 AS node_id FROM solid_mesh
                UNION ALL
                SELECT solid_id, material_tag, N4 AS node_id FROM solid_mesh
            ),
            material_node_temp AS (
                SELECT DISTINCT
                    sn.material_tag,
                    nt.timestamp_id,
                    nt.node_id,
                    nt.Temperature
                FROM solid_nodes sn
                JOIN node_temperatures nt ON sn.node_id = nt.node_id
            )
            SELECT
                mnt.material_tag                                             AS material_id,
                COALESCE(ml.material_name, CAST(mnt.material_tag AS TEXT)) AS material_section_lookup,
                ts.time                                                     AS timestep,
                AVG(mnt.Temperature)                                        AS avg_temp_material,
                MAX(mnt.Temperature)                                        AS max_temp_material
            FROM material_node_temp mnt
            JOIN timestamps ts     ON mnt.timestamp_id = ts.id
            LEFT JOIN material_list ml ON mnt.material_tag = ml.material_tag
            GROUP BY mnt.material_tag, material_section_lookup, ts.time
            ORDER BY ts.time, mnt.material_tag
            """
        )

    def get_fire_curve(self) -> pd.DataFrame:
        """Return the fire-curve (ambient temperature vs. time).

        Columns: ``time``, ``temperature``

        Returns an empty DataFrame when the ``temperature_curve`` table is absent.
        """
        if not self._table_exists("temperature_curve"):
            return pd.DataFrame(columns=["time", "temperature"])
        return self._query(
            "SELECT time, temperature FROM temperature_curve ORDER BY time"
        )
