"""
apps/thermal_viewer.py
~~~~~~~~~~~~~~~~~~~~~~
SAFIR 2-D Thermal Results Viewer – Bokeh Server application.

Launch standalone with::

    bokeh serve apps/thermal_viewer.py ^
        --port 5006 ^
        --allow-websocket-origin=* ^
        --log-level=info

The thermal app is then reachable at ``http://localhost:5006/thermal_viewer``.

To specify the database path set the environment variable or pass it via
the Bokeh ``--args`` flag::

    set SAFIR_DB_PATH=C:\\path\\to\\Raw.db
    bokeh serve apps/thermal_viewer.py --show --allow-websocket-origin=*

    # -- or --
    bokeh serve apps/thermal_viewer.py --show --allow-websocket-origin=* ^
        --args --db C:\\path\\to\\Raw.db

When embedded via FastAPI (``server_document``), the path is passed as the
``db`` URL argument.

All SQL queries are kept in ``database/queries_thermal.py``.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import (
    BasicTicker,
    ColorBar,
    ColumnDataSource,
    Div,
    HoverTool,
    LinearColorMapper,
    Select,
    Slider,
)
from bokeh.palettes import Plasma256
from bokeh.plotting import curdoc, figure

# ---------------------------------------------------------------------------
# Add the project root to sys.path so database.queries_thermal can be imported
# regardless of the working directory used by ``bokeh serve``.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import database.queries_thermal as dbq  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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
# a URL query argument ``?db=<path>``.
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

def _resolve_db_path(raw: str) -> str:
    """Resolve *raw* to an absolute path and warn if the file is missing."""
    p = Path(raw).expanduser().resolve()
    if not p.is_file():
        logger.warning("Database file not found at resolved path: %s", p)
    return str(p)


db_path = _resolve_db_path(db_path)
logger.info("Thermal viewer using database: %s", db_path)

# ---------------------------------------------------------------------------
# Load static lists once at startup
# ---------------------------------------------------------------------------

try:
    _sections_df = dbq.get_thermal_sections(db_path)
    _timesteps_df = dbq.get_thermal_timesteps(db_path)
except Exception as exc:  # noqa: BLE001
    logger.error("Failed to load thermal sections/timesteps: %s", exc)
    _sections_df = pd.DataFrame(columns=["section_id"])
    _timesteps_df = pd.DataFrame(columns=["id", "time"])

_section_ids: list[str] = (
    [str(s) for s in _sections_df["section_id"].tolist()]
    if not _sections_df.empty
    else []
)
_timestep_ids: list[int] = (
    _timesteps_df["id"].tolist() if not _timesteps_df.empty else []
)
_timestep_times: list[float] = (
    _timesteps_df["time"].tolist() if not _timesteps_df.empty else []
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

header_div = Div(
    text=(
        '<div style="font-size:1.5rem;font-weight:700;color:#c91919;margin-bottom:0.3rem;">'
        "SAFIR 2-D Thermal Results Viewer"
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
# ── SECTION 1: 2-D Temperature Field ──
# ---------------------------------------------------------------------------

section_select = Select(
    title="Section / Element",
    value=_section_ids[0] if _section_ids else "",
    options=_section_ids if _section_ids else ["(no sections)"],
    width=200,
)

# Timestep slider (index into _timestep_ids list)
_n_steps = max(len(_timestep_ids) - 1, 0)
timestep_slider = Slider(
    title="Time step index",
    start=0,
    end=_n_steps,
    step=1,
    value=0,
    width=500,
)

time_label_div = Div(
    text="",
    width=300,
    styles={"font-size": "0.85rem", "color": "#555", "line-height": "2rem"},
)

# Temperature field data source
field_source = ColumnDataSource(
    data={"x": [], "y": [], "temperature": [], "node_id": []}
)

# Color mapper
color_mapper = LinearColorMapper(
    palette=Plasma256,
    low=0.0,
    high=1000.0,
)

# Main 2-D temperature field plot
field_fig = figure(
    title="2-D Temperature Field",
    x_axis_label="x (m)",
    y_axis_label="y (m)",
    width=700,
    height=500,
    tools="pan,wheel_zoom,box_zoom,reset,save,tap",
    match_aspect=True,
)
field_fig.add_tools(
    HoverTool(
        tooltips=[
            ("Node", "@node_id"),
            ("x", "@x{0.4f} m"),
            ("y", "@y{0.4f} m"),
            ("Temperature", "@temperature{0.1f} °C"),
        ]
    )
)

field_fig.scatter(
    "x",
    "y",
    source=field_source,
    marker="circle",
    size=8,
    fill_color={"field": "temperature", "transform": color_mapper},
    line_color=None,
)

color_bar = ColorBar(
    color_mapper=color_mapper,
    ticker=BasicTicker(desired_num_ticks=10),
    label_standoff=8,
    border_line_color=None,
    title="°C",
    width=12,
)
field_fig.add_layout(color_bar, "right")

field_info_div = Div(
    text="",
    width=900,
    styles={"font-size": "0.85rem", "color": "#555"},
)

# ---------------------------------------------------------------------------
# ── SECTION 2: Temperature vs Time for a selected node ──
# ---------------------------------------------------------------------------

selected_node_div = Div(
    text='<i style="color:#aaa;">Click a node in the temperature field to see its history.</i>',
    width=900,
    styles={"font-size": "0.85rem"},
)

history_source = ColumnDataSource(data={"time": [], "temperature": []})

history_fig = figure(
    title="Temperature vs Time (selected node)",
    x_axis_label="Time (s)",
    y_axis_label="Temperature (°C)",
    width=900,
    height=300,
    tools="pan,wheel_zoom,box_zoom,reset,save",
)
history_fig.add_tools(
    HoverTool(
        tooltips=[("Time", "@time{0.1f} s"), ("Temperature", "@temperature{0.1f} °C")]
    )
)
history_fig.line(
    "time",
    "temperature",
    source=history_source,
    line_width=2,
    color="#c91919",
)
history_fig.scatter(
    "time",
    "temperature",
    source=history_source,
    marker="circle",
    size=5,
    color="#c91919",
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

# Cached node ID for history updates
_selected_node_id: list[int | None] = [None]


def _current_section() -> str:
    return section_select.value


def _current_timestep_id() -> int | None:
    idx = int(timestep_slider.value)
    if 0 <= idx < len(_timestep_ids):
        return _timestep_ids[idx]
    return None


def _current_time() -> float | None:
    idx = int(timestep_slider.value)
    if 0 <= idx < len(_timestep_times):
        return _timestep_times[idx]
    return None


def _update_field(attr, old, new) -> None:  # noqa: ANN001
    sec = _current_section()
    ts_id = _current_timestep_id()
    t = _current_time()

    if not sec or ts_id is None:
        field_source.data = {"x": [], "y": [], "temperature": [], "node_id": []}
        return

    try:
        df = dbq.get_temperature_grid(db_path, sec, ts_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_temperature_grid failed: %s", exc)
        df = pd.DataFrame(columns=["node_id", "x", "y", "temperature"])

    if df.empty:
        field_source.data = {"x": [], "y": [], "temperature": [], "node_id": []}
        field_info_div.text = f"<b>Section {sec}</b> – no thermal data found for this time step."
        time_label_div.text = f"<b>t = {t:.1f} s</b>" if t is not None else ""
        return

    # Filter out rows with NaN temperatures (no data for this timestep)
    df = df.dropna(subset=["temperature"])

    if df.empty:
        field_source.data = {"x": [], "y": [], "temperature": [], "node_id": []}
        field_info_div.text = f"<b>Section {sec}</b> – no thermal data found for this time step."
        time_label_div.text = f"<b>t = {t:.1f} s</b>" if t is not None else ""
        return

    temps = df["temperature"].tolist()
    t_min = min(temps)
    t_max = max(temps)
    # Keep a small spread so the color bar is always meaningful
    if t_max - t_min < 1.0:
        t_max = t_min + 1.0
    color_mapper.low = t_min
    color_mapper.high = t_max

    field_source.data = {
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "temperature": temps,
        "node_id": df["node_id"].tolist(),
    }

    field_fig.title.text = (
        f"2-D Temperature Field  |  Section {sec}"
        + (f"  |  t = {t:.1f} s" if t is not None else "")
    )
    time_label_div.text = f"<b>t = {t:.1f} s</b>" if t is not None else ""
    field_info_div.text = (
        f"<b>Section {sec}</b>"
        f" &nbsp;|&nbsp; {len(df)} nodes"
        f" &nbsp;|&nbsp; T<sub>min</sub> = {t_min:.1f} °C"
        f" &nbsp;|&nbsp; T<sub>max</sub> = {t_max:.1f} °C"
    )


def _update_history(node_id: int) -> None:
    sec = _current_section()
    _selected_node_id[0] = node_id
    try:
        df = dbq.get_temperature_history(db_path, sec, node_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_temperature_history failed: %s", exc)
        df = pd.DataFrame(columns=["time", "temperature"])

    if df.empty:
        history_source.data = {"time": [], "temperature": []}
        selected_node_div.text = f"<b>Node {node_id}</b> – no temperature history found."
        history_fig.title.text = f"Temperature vs Time (Node {node_id}) – no data"
        return

    history_source.data = {
        "time": df["time"].tolist(),
        "temperature": df["temperature"].tolist(),
    }
    history_fig.title.text = f"Temperature vs Time  (Node {node_id})"
    selected_node_div.text = (
        f"<b>Node {node_id}</b>"
        f" &nbsp;|&nbsp; {len(df)} time steps"
        f" &nbsp;|&nbsp; T<sub>max</sub> = {df['temperature'].max():.1f} °C"
    )


def _on_tap(event) -> None:  # noqa: ANN001
    """Handle tap/click on the field plot to select a node."""
    indices = field_source.selected.indices
    if not indices:
        return
    idx = indices[0]
    node_ids = field_source.data.get("node_id", [])
    if idx < len(node_ids):
        _update_history(int(node_ids[idx]))


field_source.selected.on_change("indices", lambda attr, old, new: _on_tap(None))  # type: ignore[arg-type]

section_select.on_change("value", _update_field)
timestep_slider.on_change("value", _update_field)

# ---------------------------------------------------------------------------
# Assemble layout
# ---------------------------------------------------------------------------


def _hr() -> Div:
    return Div(text='<hr style="border:1px solid #ddd;margin:1rem 0;">', width=900)


layout = column(
    header_div,
    status_div,
    _hr(),
    Div(text="<b>2-D Temperature Field</b>", width=900),
    row(section_select, timestep_slider, time_label_div),
    field_info_div,
    field_fig,
    _hr(),
    Div(text="<b>Temperature History (click a node above)</b>", width=900),
    selected_node_div,
    history_fig,
)

curdoc().add_root(layout)
curdoc().title = "SAFIR Thermal Viewer"

# ---------------------------------------------------------------------------
# Initial load
# ---------------------------------------------------------------------------

if _section_ids and _timestep_ids:
    _update_field(None, None, None)
    status_div.text = (
        f'<span style="color:#2ca02c;font-size:0.85rem;">'
        f"✓ Loaded {len(_section_ids)} section(s), {len(_timestep_ids)} time step(s)."
        "</span>"
    )
    logger.info(
        "SAFIR Thermal Viewer ready (%d sections, %d timesteps)",
        len(_section_ids),
        len(_timestep_ids),
    )
else:
    status_div.text = (
        '<span style="color:#856404;font-size:0.85rem;">'
        "⚠ No thermal data found in the database. "
        "Expected tables: <code>node_coordinates</code>, <code>node_temperatures</code>, "
        "<code>timestamps</code>."
        "</span>"
    )
    logger.warning("No thermal data available in database: %s", db_path)
