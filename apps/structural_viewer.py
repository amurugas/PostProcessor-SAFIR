"""
apps/structural_viewer.py
~~~~~~~~~~~~~~~~~~~~~~~~~
SAFIR Structural Results Viewer – Bokeh Server application.

Launch with::

    bokeh serve apps/structural_viewer.py --show --allow-websocket-origin=* --port 5007

To specify the database path use the environment variable or the Bokeh
``--args`` flag::

    set SAFIR_DB_PATH=C:\\path\\to\\Raw.db
    bokeh serve apps/structural_viewer.py --show --allow-websocket-origin=* --port 5007

    # -- or --
    bokeh serve apps/structural_viewer.py --show --allow-websocket-origin=* --port 5007 ^
        --args --db C:\\path\\to\\Raw.db

When embedded via FastAPI (``apps/fastapi_structural.py``), the database path
is passed as the ``db`` URL argument.

All SQL queries are kept in ``database/queries_structural.py``.
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource,
    Div,
    HoverTool,
    Select,
)
from bokeh.plotting import curdoc, figure

# ---------------------------------------------------------------------------
# Add the project root to sys.path so database.queries_structural can be
# imported regardless of the working directory used by ``bokeh serve``.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database.queries_structural as db_queries  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (inline – no external config module required)
# ---------------------------------------------------------------------------

_DEFAULT_GAUSS_POINT: int = 1

# ---------------------------------------------------------------------------
# Resolve database path
# ---------------------------------------------------------------------------

db_path: str = os.environ.get("SAFIR_DB_PATH", "Raw.db")

# Support --args --db <path> on the Bokeh CLI
_args = sys.argv[1:]
for _i, _arg in enumerate(_args):
    if _arg == "--db" and _i + 1 < len(_args):
        db_path = _args[_i + 1]
        break

# When embedded via FastAPI / server_document, the database path is passed as
# a URL query argument ``?db=<path>``.  This is checked after the CLI flag so
# that an explicit --args --db value still wins.
try:
    _sc = curdoc().session_context
    if _sc is not None:
        _sc_db = _sc.request.arguments.get("db", [b""])[0]
        if _sc_db:
            _sc_db_str = _sc_db.decode("utf-8") if isinstance(_sc_db, bytes) else str(_sc_db)
            if _sc_db_str:
                db_path = _sc_db_str
                logger.info("Database path from session URL arg: %s", db_path)
except Exception as _exc:  # noqa: BLE001
    logger.debug("Could not read session_context URL args: %s", _exc)

logger.info("Using database: %s", db_path)


def _resolve_db_path(raw: str) -> str:
    """Resolve *raw* to an absolute path and warn if the file is missing."""
    p = Path(raw).expanduser().resolve()
    if not p.is_file():
        logger.warning("Database file not found at resolved path: %s", p)
    return str(p)


db_path = _resolve_db_path(db_path)

# ---------------------------------------------------------------------------
# Load static lists once at startup
# ---------------------------------------------------------------------------

try:
    _beam_df = db_queries.get_beam_list(db_path)
    _node_df = db_queries.get_node_list(db_path)
except Exception as exc:  # noqa: BLE001
    logger.error("Failed to load beam/node lists: %s", exc)
    _beam_df = pd.DataFrame(columns=["beam_id", "section"])
    _node_df = pd.DataFrame(columns=["node_id", "x", "y", "z"])

_beam_ids: list[str] = [str(b) for b in _beam_df["beam_id"].tolist()] if not _beam_df.empty else []
_node_ids: list[str] = [str(n) for n in _node_df["node_id"].tolist()] if not _node_df.empty else []

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

header_div = Div(
    text=(
        '<div style="font-size:1.5rem;font-weight:700;color:#c91919;margin-bottom:0.3rem;">'
        "SAFIR Structural Results Viewer"
        "</div>"
        f'<div style="color:#555;font-size:0.85rem;">Database: {db_path}</div>'
    ),
    width=900,
)

status_div = Div(
    text='<span style="color:#555;font-size:0.85rem;">Ready.</span>',
    width=900,
)

# ---------------------------------------------------------------------------
# ── SECTION 1: Beam Force vs Time ──
# ---------------------------------------------------------------------------

_FORCE_COLORS = {
    "N":  "#1f77b4",
    "Mz": "#ff7f0e",
    "My": "#2ca02c",
    "Vz": "#d62728",
    "Vy": "#9467bd",
}

beam_select = Select(
    title="Beam ID",
    value=_beam_ids[0] if _beam_ids else "",
    options=_beam_ids,
    width=180,
)

force_sources: dict[str, ColumnDataSource] = {
    comp: ColumnDataSource(data={"time": [], "value": []})
    for comp in _FORCE_COLORS
}

force_fig = figure(
    title="Beam Force vs Time",
    x_axis_label="Time (s)",
    y_axis_label="Force / Moment (N or N·m)",
    width=900,
    height=350,
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
force_fig.add_tools(HoverTool(tooltips=[("Time", "@time{0.0}"), ("Value", "@value{0.000e}")]))

for comp, color in _FORCE_COLORS.items():
    force_fig.line(
        "time",
        "value",
        source=force_sources[comp],
        line_width=2,
        color=color,
        legend_label=comp,
    )

force_fig.legend.click_policy = "hide"
force_fig.legend.location = "top_left"

beam_section_div = Div(
    text="",
    width=900,
    styles={"font-size": "0.85rem", "color": "#555"},
)


def _update_beam_force(attr, old, new) -> None:  # noqa: ANN001
    bid = beam_select.value
    if not bid:
        return
    try:
        df = db_queries.get_beam_force_history(
            db_path, int(bid), _DEFAULT_GAUSS_POINT
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("beam_force query failed for beam %s: %s", bid, exc)
        df = pd.DataFrame()

    for comp in _FORCE_COLORS:
        if not df.empty and comp in df.columns:
            force_sources[comp].data = {
                "time": df["time"].tolist(),
                "value": df[comp].tolist(),
            }
        else:
            force_sources[comp].data = {"time": [], "value": []}

    # Show section label in sub-header
    row_match = _beam_df[_beam_df["beam_id"] == int(bid)]
    section = row_match["section"].iloc[0] if not row_match.empty else "N/A"
    beam_section_div.text = (
        f'<b>Beam {bid}</b> – section: <code>{section}</code>'
        f' &nbsp;|&nbsp; Gauss point: {_DEFAULT_GAUSS_POINT}'
        f' &nbsp;|&nbsp; {len(df)} time steps'
    )
    force_fig.title.text = f"Beam Force vs Time  (Beam {bid})"


beam_select.on_change("value", _update_beam_force)

# ---------------------------------------------------------------------------
# ── SECTION 2: Node Displacement vs Time ──
# ---------------------------------------------------------------------------

_DISP_COLORS = {"D1": "#1f77b4", "D2": "#ff7f0e", "D3": "#2ca02c"}

node_select = Select(
    title="Node ID",
    value=_node_ids[0] if _node_ids else "",
    options=_node_ids,
    width=180,
)

disp_sources: dict[str, ColumnDataSource] = {
    dof: ColumnDataSource(data={"time": [], "value": []})
    for dof in _DISP_COLORS
}

disp_fig = figure(
    title="Node Displacement vs Time",
    x_axis_label="Time (s)",
    y_axis_label="Displacement (m)",
    width=900,
    height=350,
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
disp_fig.add_tools(HoverTool(tooltips=[("Time", "@time{0.0}"), ("Value", "@value{0.000e}")]))

for dof, color in _DISP_COLORS.items():
    disp_fig.line(
        "time",
        "value",
        source=disp_sources[dof],
        line_width=2,
        color=color,
        legend_label=dof,
    )

disp_fig.legend.click_policy = "hide"
disp_fig.legend.location = "top_left"

node_coord_div = Div(
    text="",
    width=900,
    styles={"font-size": "0.85rem", "color": "#555"},
)


def _update_node_displacement(attr, old, new) -> None:  # noqa: ANN001
    nid = node_select.value
    if not nid:
        return
    try:
        df = db_queries.get_node_displacement_history(db_path, int(nid))
    except Exception as exc:  # noqa: BLE001
        logger.warning("node_displacement query failed for node %s: %s", nid, exc)
        df = pd.DataFrame()

    for dof in _DISP_COLORS:
        if not df.empty and dof in df.columns:
            disp_sources[dof].data = {
                "time": df["time"].tolist(),
                "value": df[dof].tolist(),
            }
        else:
            disp_sources[dof].data = {"time": [], "value": []}

    # Show node coordinates in sub-header
    row_match = _node_df[_node_df["node_id"] == int(nid)]
    if not row_match.empty:
        r = row_match.iloc[0]
        coords = f"x={r['x']:.3f}  y={r['y']:.3f}  z={r['z']:.3f}" if "z" in r.index else f"x={r['x']:.3f}  y={r['y']:.3f}"
    else:
        coords = "N/A"
    node_coord_div.text = (
        f'<b>Node {nid}</b> – coordinates: <code>{coords}</code>'
        f' &nbsp;|&nbsp; {len(df)} time steps'
    )
    disp_fig.title.text = f"Node Displacement vs Time  (Node {nid})"


node_select.on_change("value", _update_node_displacement)

# ---------------------------------------------------------------------------
# ── SECTION 3: Fiber Result vs Time ──
# ---------------------------------------------------------------------------

fiber_beam_select = Select(
    title="Beam ID (fiber)",
    value=_beam_ids[0] if _beam_ids else "",
    options=_beam_ids,
    width=180,
)

fiber_type_select = Select(
    title="Fiber result type",
    value="stress",
    options=[("stress", "Stress (Pa)"), ("strain", "Strain (m/m)")],
    width=180,
)

# Single ColumnDataSource – one line per fiber drawn dynamically
fiber_source = ColumnDataSource(data={"time": [], "value": [], "fiber_index": []})

fiber_fig = figure(
    title="Fiber Result vs Time",
    x_axis_label="Time (s)",
    y_axis_label="Stress (Pa) / Strain (m/m)",
    width=900,
    height=350,
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
fiber_fig.add_tools(
    HoverTool(tooltips=[("Time", "@time{0.0}"), ("Fiber", "@fiber_index"), ("Value", "@value{0.000e}")])
)

# Placeholder – lines are rebuilt in callback; this keeps the plot from
# triggering the W-1000 "no renderers" warning when data is absent.
_fiber_placeholder_src = ColumnDataSource(data={"time": [], "value": [], "fiber_index": []})
fiber_fig.line("time", "value", source=_fiber_placeholder_src, line_width=0, visible=False)
_fiber_renderers: list = []

fiber_info_div = Div(
    text="",
    width=900,
    styles={"font-size": "0.85rem", "color": "#555"},
)

_FIBER_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def _update_fiber(attr, old, new) -> None:  # noqa: ANN001
    bid = fiber_beam_select.value
    ftype = fiber_type_select.value
    if not bid:
        return
    try:
        df = db_queries.get_fiber_data(
            db_path, int(bid), _DEFAULT_GAUSS_POINT, ftype
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("fiber query failed for beam %s: %s", bid, exc)
        df = pd.DataFrame()

    # Remove existing renderers
    for r in list(_fiber_renderers):
        fiber_fig.renderers.remove(r)
    _fiber_renderers.clear()

    if df.empty:
        fiber_info_div.text = f"<b>Beam {bid}</b> – no fiber data found."
        fiber_fig.title.text = f"Fiber {ftype.capitalize()} vs Time  (Beam {bid})"
        return

    fiber_indices = sorted(df["fiber_index"].unique())
    unit = "Pa" if ftype == "stress" else "m/m"
    fiber_fig.yaxis.axis_label = f"{ftype.capitalize()} ({unit})"

    for i, fidx in enumerate(fiber_indices):
        fdf = df[df["fiber_index"] == fidx].sort_values("time")
        src = ColumnDataSource(
            data={
                "time": fdf["time"].tolist(),
                "value": fdf["value"].tolist(),
                "fiber_index": [int(fidx)] * len(fdf),
            }
        )
        color = _FIBER_PALETTE[i % len(_FIBER_PALETTE)]
        r = fiber_fig.line(
            "time",
            "value",
            source=src,
            line_width=1.5,
            color=color,
            legend_label=f"Fiber {int(fidx)}",
        )
        _fiber_renderers.append(r)

    fiber_fig.legend.click_policy = "hide"
    fiber_fig.legend.location = "top_left"
    fiber_fig.title.text = f"Fiber {ftype.capitalize()} vs Time  (Beam {bid})"
    fiber_info_div.text = (
        f'<b>Beam {bid}</b> – {ftype} | {len(fiber_indices)} fibers'
        f' | Gauss point: {_DEFAULT_GAUSS_POINT}'
        f' | {df["time"].nunique()} time steps'
    )


fiber_beam_select.on_change("value", _update_fiber)
fiber_type_select.on_change("value", _update_fiber)

# ---------------------------------------------------------------------------
# Assemble layout
# ---------------------------------------------------------------------------

def _hr() -> Div:
    return Div(text='<hr style="border:1px solid #ddd;margin:1rem 0;">', width=900)


layout = column(
    header_div,
    status_div,
    _hr(),
    Div(text="<b>Beam Force History</b>", width=900),
    row(beam_select),
    beam_section_div,
    force_fig,
    _hr(),
    Div(text="<b>Node Displacement History</b>", width=900),
    row(node_select),
    node_coord_div,
    disp_fig,
    _hr(),
    Div(text="<b>Fiber Result History</b>", width=900),
    row(fiber_beam_select, fiber_type_select),
    fiber_info_div,
    fiber_fig,
)

curdoc().add_root(layout)
curdoc().title = "SAFIR Structural Viewer"

# ---------------------------------------------------------------------------
# Initial load
# ---------------------------------------------------------------------------

if _beam_ids:
    _update_beam_force(None, None, None)
    _update_fiber(None, None, None)

if _node_ids:
    _update_node_displacement(None, None, None)

status_div.text = (
    f'<span style="color:#2ca02c;font-size:0.85rem;">'
    f"✓ Loaded {len(_beam_ids)} beams, {len(_node_ids)} nodes."
    "</span>"
)
logger.info("SAFIR Structural Viewer ready (%d beams, %d nodes)", len(_beam_ids), len(_node_ids))
