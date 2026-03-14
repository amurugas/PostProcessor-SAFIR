"""
SAFIR-Dashboard · bokeh_app.cache_db
=====================================
Manages the lifecycle of a **temporary SQLite cache database**.

Workflow
--------
1. :class:`CacheDatabase` is instantiated with a *source* ``.db`` path.
2. :meth:`CacheDatabase.build` copies the required tables from the source
   database into a fresh temporary file and creates any performance indexes
   and convenience views.
3. The cache path is exposed via :attr:`CacheDatabase.path` so other modules
   can open plain ``sqlite3`` connections to it.
4. :meth:`CacheDatabase.close` deletes the temporary file from disk.

The class also implements the context-manager protocol so callers can use a
``with`` statement and guarantee cleanup even on error::

    with CacheDatabase(source_path) as cache:
        loader = DataLoader(cache.path)
        …
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tables copied verbatim from the source database
# ---------------------------------------------------------------------------
_CORE_TABLES = [
    "timestamps",
    "node_coordinates",
    "solid_mesh",
    "node_temperatures",
]

_OPTIONAL_TABLES = [
    "material_list",
    "frontiers",
    "temperature_curve",
    "model_data",
]

# ---------------------------------------------------------------------------
# SQL: performance indexes
# ---------------------------------------------------------------------------
_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_nt_timestamp ON node_temperatures(timestamp_id);
CREATE INDEX IF NOT EXISTS idx_nt_node      ON node_temperatures(node_id);
CREATE INDEX IF NOT EXISTS idx_ts_time      ON timestamps(time);
CREATE INDEX IF NOT EXISTS idx_nc_node      ON node_coordinates(node_id);
CREATE INDEX IF NOT EXISTS idx_sm_solid     ON solid_mesh(solid_id);
CREATE INDEX IF NOT EXISTS idx_sm_material  ON solid_mesh(material_tag);
"""

# ---------------------------------------------------------------------------
# SQL: convenience views
# ---------------------------------------------------------------------------
_VW_SOLID_NODES = """
DROP VIEW IF EXISTS vw_solid_nodes;
CREATE VIEW vw_solid_nodes AS
    SELECT solid_id, material_tag, N1 AS node_id FROM solid_mesh
    UNION ALL
    SELECT solid_id, material_tag, N2 AS node_id FROM solid_mesh
    UNION ALL
    SELECT solid_id, material_tag, N3 AS node_id FROM solid_mesh
    UNION ALL
    SELECT solid_id, material_tag, N4 AS node_id FROM solid_mesh;
"""

_VW_MATERIAL_TEMP_SUMMARY = """
DROP VIEW IF EXISTS vw_material_temperature_summary;
CREATE VIEW vw_material_temperature_summary AS
WITH material_node_temp AS (
    SELECT DISTINCT
        vsn.material_tag,
        nt.timestamp_id,
        nt.node_id,
        nt.Temperature
    FROM vw_solid_nodes vsn
    JOIN node_temperatures nt ON vsn.node_id = nt.node_id
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
ORDER BY ts.time, mnt.material_tag;
"""


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    """Return *True* if *name* is a table (not a view) in *conn*."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _copy_table(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
) -> None:
    """Bulk-copy all rows of *table* from *src* to *dst*.

    The schema is recreated with ``CREATE TABLE … AS SELECT … WHERE 0`` then
    rows are inserted with ``INSERT INTO … SELECT …``.  Both connections must
    be to *different* databases.
    """
    # Attach the source database to the destination connection so we can use
    # plain SQL for the transfer without loading everything into Python memory.
    src_path = src.execute("PRAGMA database_list").fetchone()[2]
    dst.execute(f"ATTACH DATABASE '{src_path}' AS _src")
    try:
        # Re-create schema
        schema_row = dst.execute(
            "SELECT sql FROM _src.sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if schema_row is None:
            return
        dst.execute(schema_row[0])
        # Copy data
        dst.execute(f"INSERT INTO main.{table} SELECT * FROM _src.{table}")
        dst.commit()
    finally:
        dst.execute("DETACH DATABASE _src")


class CacheDatabase:
    """Temporary SQLite cache that mirrors selected tables from a source DB.

    Parameters
    ----------
    source_path:
        Filesystem path to the SAFIR ``.db`` file to read from.
    cache_dir:
        Directory in which the temp file is created.  Defaults to the OS
        temp directory.
    """

    def __init__(
        self,
        source_path: str | Path,
        cache_dir: Optional[str | Path] = None,
    ) -> None:
        self._source_path = Path(source_path)
        self._cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir())
        self._tmp_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def path(self) -> str:
        """Filesystem path to the temporary cache database."""
        if self._tmp_path is None:
            raise RuntimeError("Cache database has not been built yet. Call build() first.")
        return str(self._tmp_path)

    def build(self) -> "CacheDatabase":
        """Create the cache database and populate it from the source DB.

        Returns *self* so the call can be chained::

            cache = CacheDatabase(src).build()
        """
        if not self._source_path.exists():
            raise FileNotFoundError(f"Source database not found: {self._source_path}")

        fd, tmp = tempfile.mkstemp(suffix=".db", prefix="safir_cache_", dir=self._cache_dir)
        os.close(fd)
        self._tmp_path = Path(tmp)
        logger.info("Building cache database at %s", self._tmp_path)

        src_conn = sqlite3.connect(str(self._source_path))
        dst_conn = sqlite3.connect(str(self._tmp_path))
        try:
            src_conn.execute("PRAGMA journal_mode=WAL")
            dst_conn.execute("PRAGMA journal_mode=WAL")
            dst_conn.execute("PRAGMA synchronous=OFF")

            # Copy core tables (always required)
            for table in _CORE_TABLES:
                if not _table_exists(src_conn, table):
                    raise ValueError(
                        f"Source database is missing required table: '{table}'"
                    )
                _copy_table(src_conn, dst_conn, table)
                logger.debug("Copied table: %s", table)

            # Copy optional tables when present
            for table in _OPTIONAL_TABLES:
                if _table_exists(src_conn, table):
                    _copy_table(src_conn, dst_conn, table)
                    logger.debug("Copied optional table: %s", table)

            # Build indexes and views
            dst_conn.executescript(_INDEX_SQL)
            dst_conn.executescript(_VW_SOLID_NODES)

            has_material_list = _table_exists(dst_conn, "material_list")
            if has_material_list:
                dst_conn.executescript(_VW_MATERIAL_TEMP_SUMMARY)

            dst_conn.commit()
        finally:
            src_conn.close()
            dst_conn.close()

        logger.info("Cache database built successfully.")
        return self

    def close(self) -> None:
        """Delete the temporary cache database from disk."""
        if self._tmp_path and self._tmp_path.exists():
            try:
                self._tmp_path.unlink()
                logger.info("Cache database deleted: %s", self._tmp_path)
            except OSError as exc:
                logger.warning("Could not delete cache database: %s", exc)
        self._tmp_path = None

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "CacheDatabase":
        return self.build()

    def __exit__(self, *_) -> None:
        self.close()
