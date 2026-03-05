"""
shared.data.processors
~~~~~~~~~~~~~~~~~~~~~~~
Data processing pipelines for SAFIR post-processing results.

Classes
-------
TemperatureProcessor
    Aggregates and analyses node-temperature data from a thermal database.
DisplacementProcessor
    Extracts and summarises node-displacement data from a structural database.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


class TemperatureProcessor:
    """Compute temperature statistics from a thermal SAFIR database.

    Parameters
    ----------
    db_path:
        Path to the SQLite database managed by
        :class:`~shared.database.thermal_db.ThermalDatabaseManager`.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def calc_max_temp_by_material(self) -> list[dict]:
        """Return the peak temperature per material across all time-steps.

        Returns
        -------
        list[dict]
            Each entry has keys ``material_tag``, ``material_name``,
            ``timestamp_id``, and ``max_temp``.
        """
        query = """
            SELECT
                ml.material_tag,
                ml.material_name,
                nt.timestamp_id,
                MAX(nt.Temperature) AS max_temp
            FROM node_temperatures nt
            JOIN solid_mesh sm ON nt.node_id IN (sm.N1, sm.N2, sm.N3, sm.N4)
            JOIN material_list ml ON sm.material_tag = ml.material_tag
            GROUP BY ml.material_tag, nt.timestamp_id
            ORDER BY ml.material_tag, nt.timestamp_id
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()

        results = [
            {
                "material_tag": r[0],
                "material_name": r[1],
                "timestamp_id": r[2],
                "max_temp": r[3],
            }
            for r in rows
        ]
        logger.info(
            "Computed max temperatures for %d material×timestep combinations.",
            len(results),
        )
        return results

    def get_avg_temp_by_material(self) -> dict[int, dict]:
        """Return average temperature over time per material.

        Returns
        -------
        dict[int, dict]
            Keys are ``material_tag`` integers.  Each value is a dict with
            lists ``"timestamps"`` and ``"avg_temps"``.
        """
        query = """
            SELECT
                ml.material_tag,
                t.time,
                AVG(nt.Temperature) AS avg_temp
            FROM node_temperatures nt
            JOIN timestamps t ON nt.timestamp_id = t.id
            JOIN solid_mesh sm ON nt.node_id IN (sm.N1, sm.N2, sm.N3, sm.N4)
            JOIN material_list ml ON sm.material_tag = ml.material_tag
            GROUP BY ml.material_tag, t.time
            ORDER BY ml.material_tag, t.time
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()

        result: dict[int, dict] = {}
        for mat_tag, time, avg_temp in rows:
            if mat_tag not in result:
                result[mat_tag] = {"timestamps": [], "avg_temps": []}
            result[mat_tag]["timestamps"].append(time)
            result[mat_tag]["avg_temps"].append(avg_temp)

        return result


class DisplacementProcessor:
    """Extract and summarise node-displacement data from a structural database.

    Parameters
    ----------
    db_path:
        Path to the SQLite database managed by
        :class:`~shared.database.structural_db.StructuralDatabaseManager`.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_displacement_time_series(
        self, node_id: int, dof: str = "D1"
    ) -> tuple[list[float], list[float]]:
        """Return the time-history of a single DOF for one node.

        Parameters
        ----------
        node_id:
            Node identifier.
        dof:
            Degree-of-freedom column name (``"D1"`` … ``"D7"``).

        Returns
        -------
        tuple[list[float], list[float]]
            ``(times, displacements)`` parallel lists.
        """
        valid_dofs = {"D1", "D2", "D3", "D4", "D5", "D6", "D7"}
        if dof not in valid_dofs:
            raise ValueError(
                f"Invalid DOF '{dof}'. Must be one of {sorted(valid_dofs)}."
            )

        query = f"""
            SELECT t.time, nd.{dof}
            FROM   node_displacements nd
            JOIN   timestamps t ON nd.timestamp_id = t.id
            WHERE  nd.node_id = ?
            ORDER  BY t.time
        """  # noqa: S608 – dof validated above
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, (node_id,))
            rows = cur.fetchall()

        times = [r[0] for r in rows]
        disps = [r[1] for r in rows]
        return times, disps

    def get_max_displacement_per_node(self, dof: str = "D1") -> list[dict]:
        """Return the maximum displacement in *dof* per node.

        Parameters
        ----------
        dof:
            Degree-of-freedom column name.

        Returns
        -------
        list[dict]
            Each entry has ``node_id`` and ``max_disp`` keys.
        """
        valid_dofs = {"D1", "D2", "D3", "D4", "D5", "D6", "D7"}
        if dof not in valid_dofs:
            raise ValueError(
                f"Invalid DOF '{dof}'. Must be one of {sorted(valid_dofs)}."
            )

        query = f"""
            SELECT node_id, MAX(ABS({dof})) AS max_disp
            FROM   node_displacements
            GROUP  BY node_id
            ORDER  BY node_id
        """  # noqa: S608 – dof validated above
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()

        return [{"node_id": r[0], "max_disp": r[1]} for r in rows]
