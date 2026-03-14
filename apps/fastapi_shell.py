"""
apps/fastapi_shell.py
~~~~~~~~~~~~~~~~~~~~~
FastAPI web shell for the SAFIR Results Viewer.

This module provides:
- A landing page (``/``) with a case-picker dropdown and viewer-type selector
- Discovery of SAFIR cases from a local folder tree
- Embedding of either the Bokeh structural viewer or the Bokeh thermal viewer
  for the selected case

Architecture
------------
- FastAPI (port 8000) – web shell, landing page, case list
- Bokeh Server (port 5006) – interactive structural plots  (``/structural_viewer``)
                           – interactive thermal plots    (``/thermal_viewer``)

Start both servers before opening the browser (see ``launch_fastapi.bat``
and ``launch_bokeh.bat`` for Windows convenience scripts).

Configuration
-------------
SAFIR_CASES_DIR      Root folder that contains one sub-folder per case.
                     Each sub-folder must contain exactly one ``*.db`` file.
                     Default: ``<home>/SAFIR/Cases``

BOKEH_URL            Full URL of the Bokeh structural app.
                     Default: ``http://localhost:5006/structural_viewer``

BOKEH_THERMAL_URL    Full URL of the Bokeh thermal app.
                     Default: ``http://localhost:5006/thermal_viewer``

Example layout
--------------
<home>/SAFIR/Cases/
    Case_001/Raw.db
    Case_002/Raw.db
    ...
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from bokeh.embed import server_document
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# Add the project root to sys.path so templates can be found
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CASES_DIR: str = os.environ.get("SAFIR_CASES_DIR", str(Path.home() / "SAFIR" / "Cases"))
BOKEH_URL: str = os.environ.get("BOKEH_URL", "http://localhost:5006/structural_viewer")
BOKEH_THERMAL_URL: str = os.environ.get("BOKEH_THERMAL_URL", "http://localhost:5006/thermal_viewer")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI + Jinja2
# ---------------------------------------------------------------------------

app = FastAPI(title="SAFIR Results Viewer")
templates = Jinja2Templates(directory=str(Path(_ROOT) / "templates"))


# ---------------------------------------------------------------------------
# Case discovery
# ---------------------------------------------------------------------------


def discover_cases(cases_root: str) -> list[dict[str, str]]:
    """Scan *cases_root* and return cases that contain a SQLite database file.

    A *case* is any direct sub-folder of *cases_root* that holds at least one
    ``*.db`` file.  When multiple ``.db`` files are present the first one
    (alphabetical order) is used.

    Parameters
    ----------
    cases_root:
        Absolute or relative path to the root cases directory.

    Returns
    -------
    list[dict]
        Each entry has keys ``"name"`` (folder name) and ``"db_path"``
        (absolute path to the database file).
    """
    root = Path(cases_root)
    if not root.is_dir():
        logger.warning("Cases directory not found: %s", cases_root)
        return []

    cases: list[dict[str, str]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        db_files = sorted(entry.glob("*.db"))
        if not db_files:
            continue
        cases.append({"name": entry.name, "db_path": str(db_files[0])})

    logger.info("Found %d case(s) in %s", len(cases), cases_root)
    return cases


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def landing_page(
    request: Request,
    case: str = Query(default="", description="Selected case name"),
    viewer: str = Query(default="structural", description="Viewer type: 'structural' or 'thermal'"),
) -> HTMLResponse:
    """Render the landing page.

    Query parameters
    ----------------
    case : str
        Name of the selected case folder.  Omit or leave blank to show the
        picker without loading a viewer.
    viewer : str
        Which viewer to load: ``'structural'`` (default) or ``'thermal'``.
    """
    cases = discover_cases(CASES_DIR)
    case_map: dict[str, str] = {c["name"]: c["db_path"] for c in cases}

    # Normalise viewer type
    viewer = viewer if viewer in ("structural", "thermal") else "structural"

    bokeh_script: str | None = None
    selected_case_info: dict[str, str] | None = None
    error_message: str | None = None

    if case:
        if case not in case_map:
            error_message = (
                f"Case '{case}' was not found. Please select a valid case from the list."
            )
        else:
            db_path = case_map[case]
            if not Path(db_path).is_file():
                error_message = (
                    f"Database file not found: {db_path}"
                )
                logger.warning("DB missing for case '%s': %s", case, db_path)
            else:
                bokeh_url = BOKEH_THERMAL_URL if viewer == "thermal" else BOKEH_URL
                try:
                    bokeh_script = server_document(
                        url=bokeh_url,
                        arguments={"db": db_path},
                    )
                    selected_case_info = {"name": case, "db_path": db_path}
                except OSError as exc:
                    logger.error(
                        "Network error connecting to Bokeh (%s) for case '%s': %s",
                        bokeh_url, case, exc,
                    )
                    viewer_label = "thermal" if viewer == "thermal" else "structural"
                    error_message = (
                        f"Could not connect to the Bokeh {viewer_label} server at {bokeh_url}. "
                        "Make sure it is running (see launch_bokeh.bat)."
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to create Bokeh embed for case '%s': %s", case, exc
                    )
                    error_message = (
                        f"Failed to load the {viewer} viewer for case '{case}'. "
                        f"Check the server logs for details. ({type(exc).__name__})"
                    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "cases": cases,
            "selected_case": case,
            "selected_viewer": viewer,
            "selected_case_info": selected_case_info,
            "bokeh_script": bokeh_script,
            "error_message": error_message,
            "cases_dir": CASES_DIR,
        },
    )
