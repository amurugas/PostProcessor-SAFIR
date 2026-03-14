"""
SAFIR-Dashboard · bokeh_app.main
==================================
Bokeh server document.

Run this file with the Bokeh server::

    bokeh serve SAFIR-Dashboard/bokeh_app/main.py \\
        --args --db path/to/results.db

Or use the convenience launcher::

    python SAFIR-Dashboard/bokeh_app/server.py --db path/to/results.db

Architecture overview
---------------------
::

    server.py (CLI)
        │
        ├─ CacheDatabase.build()   → temporary SQLite cache (copy of source DB)
        │
        ├─ bokeh serve main.py     → Bokeh server process
        │       │
        │       ├─ DataLoader      → reads DataFrames from cache DB
        │       ├─ plots.*         → pure Bokeh figure builders
        │       └─ curdoc()        → Bokeh document with widgets + callbacks
        │
        └─ CacheDatabase.close()   → deletes temp file on exit

Environment variables
---------------------
``SAFIR_CACHE_DB``
    Path to the temporary cache database.  Set automatically by
    ``server.py``; may also be set manually when invoking ``bokeh serve``
    directly.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import numpy as np
import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import (
    CheckboxGroup,
    ColumnDataSource,
    Div,
    RadioGroup,
    Select,
    Slider,
    Tabs,
    TabPanel,
    Button,
)
from bokeh.plotting import curdoc

from .data_loader import DataLoader
from .plots import make_material_figure, make_node_figure, make_section_figure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve cache DB path
# ---------------------------------------------------------------------------

cache_path: Optional[str] = os.environ.get("SAFIR_CACHE_DB")

if cache_path is None:
    # Support ``bokeh serve main.py --args --db /path/to/cache.db``
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--db" and i + 1 < len(args):
            cache_path = args[i + 1]
            break

if not cache_path or not os.path.exists(cache_path):
    raise RuntimeError(
        "Cache database path not found. "
        "Set the SAFIR_CACHE_DB environment variable or use --args --db <path>."
    )

logger.info("Opening cache database: %s", cache_path)

# ---------------------------------------------------------------------------
# Load static data (loaded once per session, not per callback)
# ---------------------------------------------------------------------------

loader = DataLoader(cache_path)

time_df = loader.get_time_steps()
if time_df.empty:
    raise RuntimeError("No timestamps found in the cache database.")

coords_df = loader.get_node_coordinates()
mesh_df = loader.get_solid_mesh()
material_lookup_df = loader.get_material_lookup()
frontiers_df = loader.get_frontiers()
material_summary_df = loader.get_material_summary()
fire_df = loader.get_fire_curve()

# Get all unique node IDs for the node-history selector
all_node_ids = sorted(coords_df["node_id"].astype(int).tolist()) if not coords_df.empty else []

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _temp_unit() -> str:
    return "F" if temp_unit_radio.active == 1 else "C"


# ---------------------------------------------------------------------------
# Shared controls (top-level)
# ---------------------------------------------------------------------------

temp_unit_radio = RadioGroup(labels=["°C", "°F"], active=0, width=120)

title_div = Div(
    text=(
        '<div style="font-size:1.6rem;font-weight:700;color:#c91919;'
        'margin-bottom:0.4rem;">SAFIR DASHBOARD – 2D THERMAL</div>'
        f'<div style="color:#555;font-size:0.9rem;">Cache DB: {os.path.basename(cache_path)}</div>'
    )
)

# ---------------------------------------------------------------------------
# ── TAB 1: Section Viewer ──
# ---------------------------------------------------------------------------

time_values = time_df["time"].tolist()
time_ids = time_df["id"].tolist()

time_slider = Slider(
    start=0,
    end=max(len(time_values) - 1, 1),
    value=0,
    step=1,
    title=f"Time step  [0 – {len(time_values) - 1}]",
    width=600,
)

section_layer_options = ["Colour by temperature", "Colour by material", "Show boundaries", "Show frontiers", "Show node IDs"]
section_layers = CheckboxGroup(labels=section_layer_options, active=[0, 2])

initial_temp_df = loader.get_section_temperatures(int(time_ids[0]))

section_fig = make_section_figure(
    coords=coords_df,
    mesh=mesh_df,
    temp_df=initial_temp_df,
    material_lookup=material_lookup_df,
    frontiers=frontiers_df,
    temp_unit=_temp_unit(),
    show_temperature=0 in section_layers.active,
    show_material=1 in section_layers.active,
    show_boundary=2 in section_layers.active,
    show_frontier=3 in section_layers.active,
    show_node_ids=4 in section_layers.active,
)

section_panel_fig_holder: list = [section_fig]


def _rebuild_section() -> None:
    idx = int(time_slider.value)
    tid = int(time_ids[idx])
    temp_df = loader.get_section_temperatures(tid)
    active = set(section_layers.active)
    new_fig = make_section_figure(
        coords=coords_df,
        mesh=mesh_df,
        temp_df=temp_df,
        material_lookup=material_lookup_df,
        frontiers=frontiers_df,
        temp_unit=_temp_unit(),
        show_temperature=0 in active,
        show_material=1 in active,
        show_boundary=2 in active,
        show_frontier=3 in active,
        show_node_ids=4 in active,
    )
    section_layout.children[1] = new_fig  # type: ignore[attr-defined]


def _on_section_layer_change(attr, old, new) -> None:  # noqa: ANN001
    _rebuild_section()


def _on_time_change(attr, old, new) -> None:  # noqa: ANN001
    _rebuild_section()


time_slider.on_change("value", _on_time_change)
section_layers.on_change("active", _on_section_layer_change)
temp_unit_radio.on_change("active", lambda attr, old, new: _rebuild_section())

section_layout = column(
    row(time_slider, section_layers),
    section_fig,
)

section_tab = TabPanel(child=section_layout, title="Section Viewer")

# ---------------------------------------------------------------------------
# ── TAB 2: Material Summary ──
# ---------------------------------------------------------------------------

stat_select = Select(
    title="Statistic",
    value="avg_temp_material",
    options=[("avg_temp_material", "Average temperature"), ("max_temp_material", "Maximum temperature")],
    width=260,
)

avg_fig = make_material_figure(material_summary_df, "avg_temp_material", "Average Temperature per Material", _temp_unit())
max_fig = make_material_figure(material_summary_df, "max_temp_material", "Maximum Temperature per Material", _temp_unit())

material_layout = column(stat_select, avg_fig, max_fig)
material_tab = TabPanel(child=material_layout, title="Material Summary")


def _on_stat_or_unit_change(attr, old, new) -> None:  # noqa: ANN001
    unit = _temp_unit()
    new_avg = make_material_figure(material_summary_df, "avg_temp_material", "Average Temperature per Material", unit)
    new_max = make_material_figure(material_summary_df, "max_temp_material", "Maximum Temperature per Material", unit)
    material_layout.children[1] = new_avg  # type: ignore[attr-defined]
    material_layout.children[2] = new_max  # type: ignore[attr-defined]


stat_select.on_change("value", _on_stat_or_unit_change)
temp_unit_radio.on_change("active", lambda attr, old, new: _on_stat_or_unit_change(attr, old, new))

# ---------------------------------------------------------------------------
# ── TAB 3: Node History ──
# ---------------------------------------------------------------------------

node_options = [str(n) for n in all_node_ids]
node_select = Select(
    title="Select node",
    value=node_options[0] if node_options else "",
    options=node_options,
    width=200,
)

initial_node_id = int(node_options[0]) if node_options else None
initial_node_df = loader.get_node_history(initial_node_id) if initial_node_id is not None else pd.DataFrame()

node_fig = make_node_figure(initial_node_df, fire_df, initial_node_id, _temp_unit())

node_layout = column(node_select, node_fig)
node_tab = TabPanel(child=node_layout, title="Node History")


def _on_node_change(attr, old, new) -> None:  # noqa: ANN001
    nid = int(node_select.value) if node_select.value else None
    ndf = loader.get_node_history(nid) if nid is not None else pd.DataFrame()
    new_fig = make_node_figure(ndf, fire_df, nid, _temp_unit())
    node_layout.children[1] = new_fig  # type: ignore[attr-defined]


node_select.on_change("value", _on_node_change)
temp_unit_radio.on_change("active", lambda attr, old, new: _on_node_change(attr, old, new))

# ---------------------------------------------------------------------------
# Assemble document
# ---------------------------------------------------------------------------

tabs = Tabs(tabs=[section_tab, material_tab, node_tab])

doc_layout = column(
    row(title_div, temp_unit_radio),
    tabs,
)

curdoc().add_root(doc_layout)
curdoc().title = "SAFIR Dashboard – 2D Thermal"
