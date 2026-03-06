"""
shared.data.parsers
~~~~~~~~~~~~~~~~~~~~
Parsers for SAFIR-specific file formats.

Classes
-------
FireCurveParser
    Reads a SAFIR ``.fct`` time-temperature file.
XmlParser
    Reads a SAFIR XML results file using ``lxml.objectify``.
"""

from __future__ import annotations

import logging
import os
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fire-curve parser
# ---------------------------------------------------------------------------

class FireCurveParser:
    """Parse a SAFIR fire-curve (``.fct``) file and store data in the database.

    Parameters
    ----------
    file_path:
        Path to the ``.fct`` file.
    db:
        Database manager instance.
    """

    def __init__(self, file_path: str, db: object) -> None:
        self.file_path = os.path.abspath(file_path)
        self.db = db  # Database manager instance

    def parse(self) -> list[tuple[float, float]]:
        """Stream and parse the fire-curve file.

        Returns
        -------
        list[tuple[float, float]]
            A list of ``(time, temperature)`` tuples.

        Raises
        ------
        FileNotFoundError
            If :attr:`file_path` does not exist.
        """
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(
                f"Fire-curve file not found: {self.file_path}"
            )

        data: list[tuple[float, float]] = []
        with open(self.file_path, "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) == 2:
                    try:
                        data.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        continue

        if not data:
            logger.warning(
                "No valid time-temperature pairs found in %s", self.file_path
            )
        else:
            logger.info(
                "Parsed %d time-temperature pairs from %s",
                len(data),
                self.file_path,
            )
        return data

    def store_fire_curve(self, data: list[tuple[float, float]]) -> None:
        """Store the parsed data into the `temperature_curve` table.

        Parameters
        ----------
        data:
            A list of ``(time, temperature)`` tuples.
        """

        if not data:
            logger.warning("No data to store in the database.")
            return

        df = pd.DataFrame(data, columns=["time", "temperature"])
        df.insert(0, "id", range(1, len(df) + 1))

        with self.db.connect() as conn:
            conn.execute("DELETE FROM temperature_curve")
            df.to_sql("temperature_curve", conn, if_exists="append", index=False)

        logger.info(f"Inserted {len(data)} records into temperature_curve.")

    def parse_and_store_tables(self):
        data = self.parse()
        self.store_fire_curve(data)

# ---------------------------------------------------------------------------
# XML parser
# ---------------------------------------------------------------------------

class XmlParser:
    """Thin wrapper around ``lxml.objectify`` for SAFIR XML result files.

    Parameters
    ----------
    xml_path:
        Path to the SAFIR ``.xml`` result file.

    Examples
    --------
    ::

        parser = XmlParser("results.xml")
        root = parser.parse()
        n_nodes = int(root.SAFIR_RESULTS.NNODE)
    """

    def __init__(self, xml_path: str, db: object) -> None:
        self.xml_path = os.path.abspath(xml_path)
        self.db = db  # Database manager instance

    def parse(self):
        """Parse the XML file and return the ``lxml.objectify`` root element.

        Raises
        ------
        FileNotFoundError
            If :attr:`xml_path` does not exist.
        ImportError
            If ``lxml`` is not installed.
        """
        try:
            from lxml import objectify  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "lxml is required for XML parsing. "
                "Install it with: pip install lxml"
            ) from exc

        if not os.path.isfile(self.xml_path):
            raise FileNotFoundError(
                f"SAFIR XML file not found: {self.xml_path}"
            )

        line_count = 0  # Initialize line counter

        parser = objectify.makeparser(
            huge_tree=True,
            recover=True,
            resolve_entities=False,
            remove_comments=True,
            remove_pis=True,
            remove_blank_text=True,
            collect_ids=False,
        )

        # Feed bytes incrementally with a virtual root wrapper
        with open(self.xml_path, "rb") as f:
            parser.feed(b"<ROOT>")
            for chunk in iter(lambda: f.read(1 << 20), b""):
                line_count += chunk.count(b"\n")  # Count newlines in the chunk
                parser.feed(chunk)
            parser.feed(b"</ROOT>")
            line_count += 1  # Account for the virtual root wrapper
        root = parser.close()

        logger.info("Parsed XML file: %s", self.xml_path)
        logger.info("Total lines parsed: %.2f million", line_count / 1_000_000)  # Log total lines parsed
        return root

    def insert_timestamp(self, time: float) -> int:
        """Insert *time* into the ``timestamps`` table (or ignore duplicate).

        Returns
        -------
        int
            The ``id`` of the inserted or existing row.
        """
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO timestamps (time) VALUES (?)", (time,)
            )
            cur.execute("SELECT id FROM timestamps WHERE time = ?", (time,))
            row = cur.fetchone()
            return row[0]

    def parse_vector2(self, text):
        try:
            parts = text.strip().split()
            return float(parts[0]), float(parts[1])
        except:
            return None, None

    def parse_vector3(self, text_element):
        try:
            parts = str(text_element).strip().split()
            return float(parts[0]), float(parts[1]), float(parts[2])
        except:
            return None, None, None