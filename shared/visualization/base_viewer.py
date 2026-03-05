"""
shared.visualization.base_viewer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Abstract base class for all SAFIR result viewers.

Concrete subclasses implement :meth:`build_layout` to assemble the
framework-specific UI (Bokeh, Streamlit, Rhino, …) and :meth:`show`
to render or serve it.
"""

from abc import ABC, abstractmethod


class BaseViewer(ABC):
    """Common interface for interactive and batch result viewers.

    Parameters
    ----------
    db_path:
        Path to the SQLite database produced by a SAFIR DB-creation
        script or :class:`~shared.database.base.BaseDatabaseManager`.
    title:
        Human-readable title shown in the viewer header.
    """

    def __init__(self, db_path: str, title: str = "SAFIR Results Viewer") -> None:
        self.db_path = db_path
        self.title = title

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def build_layout(self):
        """Construct and return the viewer layout / figure object.

        Subclasses should return whatever their framework expects
        (e.g. a Bokeh ``column``, a Plotly ``Figure``, …).
        """

    @abstractmethod
    def show(self) -> None:
        """Render or serve the viewer to the user."""

    # ------------------------------------------------------------------
    # Helpers available to all subclasses
    # ------------------------------------------------------------------

    def _run_query(self, query: str, params: tuple = ()):
        """Execute *query* against the viewer's database.

        Parameters
        ----------
        query:
            SQL SELECT statement.
        params:
            Query parameters (passed as the second argument to
            :meth:`sqlite3.Cursor.execute`).

        Returns
        -------
        list[tuple]
            All result rows.
        """
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def get_all_timestamps(self) -> list[float]:
        """Return every distinct simulation time stored in the database."""
        rows = self._run_query(
            "SELECT DISTINCT time FROM timestamps ORDER BY time"
        )
        return [r[0] for r in rows]

    def get_fire_curve(self) -> tuple[list[float], list[float]]:
        """Return the fire time-temperature curve as two parallel lists."""
        rows = self._run_query(
            "SELECT time, temperature FROM temperature_curve ORDER BY time"
        )
        times = [r[0] for r in rows]
        temps = [r[1] for r in rows]
        return times, temps
