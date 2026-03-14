"""
SAFIR-Dashboard · bokeh_app.plots
====================================
Pure-function Bokeh plot builders.  Each function accepts plain Python /
pandas data and returns a configured :class:`bokeh.plotting.figure` (or a
layout widget).  No server state is touched here; all interactivity is wired
in :mod:`main`.

Available builders
------------------
- :func:`make_section_figure`   – 2-D thermal section with colour-mapped patches
- :func:`make_material_figure`  – per-material avg / max temperature vs. time
- :func:`make_node_figure`      – single-node temperature history + fire curve
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from bokeh.models import (
    ColorBar,
    ColumnDataSource,
    HoverTool,
    LabelSet,
    Legend,
    LinearColorMapper,
    Span,
)
from bokeh.palettes import Inferno256
from bokeh.plotting import figure

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_MATERIAL_PALETTE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


def _material_palette(tags: list[int]) -> dict[int, str]:
    """Map sorted material tags to distinct colours."""
    return {tag: _MATERIAL_PALETTE[i % len(_MATERIAL_PALETTE)] for i, tag in enumerate(sorted(tags))}


def _c_to_f(arr: np.ndarray) -> np.ndarray:
    return arr * 9.0 / 5.0 + 32.0


# ---------------------------------------------------------------------------
# Section viewer
# ---------------------------------------------------------------------------

def make_section_figure(
    coords: pd.DataFrame,
    mesh: pd.DataFrame,
    temp_df: pd.DataFrame,
    material_lookup: pd.DataFrame,
    frontiers: pd.DataFrame,
    temp_unit: str = "C",
    show_temperature: bool = True,
    show_material: bool = False,
    show_boundary: bool = True,
    show_frontier: bool = False,
    show_node_ids: bool = False,
) -> figure:
    """Build the 2-D section thermal view.

    Parameters
    ----------
    coords:
        DataFrame with columns ``node_id``, ``x``, ``y``.
    mesh:
        DataFrame with columns ``solid_id``, ``N1``–``N4``, ``material_tag``.
    temp_df:
        DataFrame with columns ``node_id``, ``Temperature`` for a single
        timestamp.
    material_lookup:
        DataFrame with columns ``material_tag``, ``material_name``.
    frontiers:
        DataFrame with columns ``solid_id``, ``face1``–``face4`` (``YES``/``NO``).
    temp_unit:
        ``"C"`` or ``"F"``.
    show_temperature / show_material / show_boundary / show_frontier / show_node_ids:
        Layer visibility flags.

    Returns
    -------
    bokeh.plotting.figure
    """
    if coords.empty or mesh.empty:
        p = figure(title="No geometry data available", width=700, height=500)
        return p

    # Build lookup dictionaries
    coord_map: dict[int, tuple[float, float]] = {
        int(r.node_id): (float(r.x), float(r.y))
        for r in coords.itertuples(index=False)
    }
    temp_map: dict[int, float] = (
        {int(r.node_id): float(r.Temperature) for r in temp_df.itertuples(index=False)}
        if not temp_df.empty
        else {}
    )
    material_name_map: dict[int, str] = {}
    if not material_lookup.empty and "material_tag" in material_lookup.columns:
        material_name_map = dict(
            zip(material_lookup["material_tag"].astype(int), material_lookup["material_name"])
        )
    frontier_map: dict[int, dict[str, str]] = {}
    if not frontiers.empty and "solid_id" in frontiers.columns:
        for row in frontiers.itertuples(index=False):
            frontier_map[int(row.solid_id)] = {
                "face1": str(row.face1),
                "face2": str(row.face2),
                "face3": str(row.face3),
                "face4": str(row.face4),
            }

    all_material_tags = sorted(set(int(t) for t in mesh["material_tag"].dropna()))
    color_map = _material_palette(all_material_tags)

    # Determine temperature range for colour mapper
    temps = list(temp_map.values())
    t_min = min(temps) if temps else 0.0
    t_max = max(temps) if temps else 1000.0
    if temp_unit == "F":
        t_min = float(_c_to_f(np.array([t_min]))[0])
        t_max = float(_c_to_f(np.array([t_max]))[0])

    mapper = LinearColorMapper(
        palette=Inferno256, low=t_min, high=t_max
    )

    p = figure(
        width=700,
        height=550,
        match_aspect=True,
        toolbar_location="above",
        tools="pan,wheel_zoom,box_zoom,reset,hover,save",
        title="2-D Thermal Section",
    )
    p.grid.grid_line_color = None
    p.axis.visible = False

    # ---- Build patch data ----
    xs_patches, ys_patches = [], []
    fill_colors, line_colors = [], []
    hover_texts, solid_ids = [], []
    avg_temps = []

    for row in mesh.itertuples(index=False):
        solid_id = int(row.solid_id)
        node_ids = [
            int(getattr(row, n))
            for n in ("N1", "N2", "N3", "N4")
            if pd.notna(getattr(row, n)) and int(getattr(row, n)) in coord_map
        ]
        if len(node_ids) < 3:
            continue

        pts = [coord_map[n] for n in node_ids]
        xs_patches.append([p_[0] for p_ in pts])
        ys_patches.append([p_[1] for p_ in pts])

        material_tag = int(row.material_tag) if pd.notna(row.material_tag) else -1
        node_temps = [temp_map[n] for n in node_ids if n in temp_map]
        avg_t: Optional[float] = float(np.mean(node_temps)) if node_temps else None
        avg_temps.append(avg_t)

        display_t = avg_t
        if display_t is not None and temp_unit == "F":
            display_t = float(_c_to_f(np.array([display_t]))[0])

        if show_temperature and display_t is not None:
            # colour mapped by temperature
            norm = (display_t - t_min) / (t_max - t_min + 1e-9)
            idx = int(np.clip(norm * 255, 0, 255))
            fill_colors.append(Inferno256[idx])
        elif show_material:
            fill_colors.append(color_map.get(material_tag, "#aaaaaa"))
        else:
            fill_colors.append("rgba(180,180,180,0.15)")

        line_colors.append("#6b0000" if show_boundary else "rgba(0,0,0,0)")

        mat_label = material_name_map.get(material_tag, str(material_tag))
        t_str = f"{display_t:.1f} °{temp_unit}" if display_t is not None else "N/A"
        hover_texts.append(f"Solid {solid_id} | Mat {mat_label} | Avg {t_str}")
        solid_ids.append(solid_id)

    patch_source = ColumnDataSource(dict(
        xs=xs_patches,
        ys=ys_patches,
        fill_color=fill_colors,
        line_color=line_colors,
        description=hover_texts,
        solid_id=solid_ids,
    ))

    patches = p.patches(
        xs="xs",
        ys="ys",
        fill_color="fill_color",
        line_color="line_color",
        line_width=1.2,
        source=patch_source,
    )

    p.add_tools(HoverTool(renderers=[patches], tooltips=[("", "@description")]))

    # ---- Frontier highlight ----
    if show_frontier and frontier_map:
        for row in mesh.itertuples(index=False):
            solid_id = int(row.solid_id)
            if solid_id not in frontier_map:
                continue
            node_ids = [
                int(getattr(row, n))
                for n in ("N1", "N2", "N3", "N4")
                if pd.notna(getattr(row, n)) and int(getattr(row, n)) in coord_map
            ]
            if len(node_ids) < 4:
                continue
            pts = [coord_map[n] for n in node_ids]
            faces = frontier_map[solid_id]
            edges = [(pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[3]), (pts[3], pts[0])]
            for i, fk in enumerate(["face1", "face2", "face3", "face4"]):
                if faces.get(fk, "").upper() == "YES":
                    p1, p2 = edges[i]
                    p.line(
                        x=[p1[0], p2[0]],
                        y=[p1[1], p2[1]],
                        line_color="#ff4444",
                        line_width=3,
                    )

    # ---- Node IDs ----
    if show_node_ids and not coords.empty:
        label_source = ColumnDataSource(
            dict(x=coords["x"], y=coords["y"], text=coords["node_id"].astype(str))
        )
        p.add_layout(
            LabelSet(
                x="x",
                y="y",
                text="text",
                source=label_source,
                text_font_size="9px",
                text_color="#003b8f",
            )
        )

    # ---- Colour bar ----
    if show_temperature:
        color_bar = ColorBar(
            color_mapper=mapper,
            width=12,
            title=f"°{temp_unit}",
            title_text_font_size="11px",
        )
        p.add_layout(color_bar, "right")

    return p


# ---------------------------------------------------------------------------
# Material summary figure
# ---------------------------------------------------------------------------

def make_material_figure(
    summary_df: pd.DataFrame,
    y_col: str,
    title: str,
    temp_unit: str = "C",
) -> figure:
    """Line chart: per-material temperature statistic vs. time.

    Parameters
    ----------
    summary_df:
        DataFrame with columns ``material_id``, ``material_section_lookup``,
        ``timestep``, ``avg_temp_material``, ``max_temp_material``.
    y_col:
        Column to plot on the Y axis (``"avg_temp_material"`` or
        ``"max_temp_material"``).
    title:
        Figure title string.
    temp_unit:
        ``"C"`` or ``"F"``.
    """
    p = figure(
        width=700,
        height=380,
        title=title,
        toolbar_location="above",
        tools="pan,wheel_zoom,box_zoom,reset,hover,save",
        x_axis_label="Time (s)",
        y_axis_label=f"Temperature (°{temp_unit})",
    )
    p.background_fill_color = "white"

    if summary_df.empty:
        return p

    df = summary_df.copy()
    if temp_unit == "F":
        df[y_col] = _c_to_f(df[y_col].to_numpy())

    legend_items = []
    material_ids = sorted(df["material_id"].dropna().unique().tolist())
    palette = _material_palette([int(m) for m in material_ids])

    for mat_id in material_ids:
        dfi = df[df["material_id"] == mat_id].sort_values("timestep")
        label = str(dfi["material_section_lookup"].iloc[0])
        color = palette.get(int(mat_id), "#333333")
        source = ColumnDataSource(dict(x=dfi["timestep"], y=dfi[y_col]))
        r = p.line("x", "y", source=source, line_color=color, line_width=2)
        legend_items.append((label, [r]))

    legend = Legend(items=legend_items, location="top_left", click_policy="hide")
    p.add_layout(legend, "right")
    p.add_tools(
        HoverTool(tooltips=[("Time", "@x{0.0}"), ("Temp", "@y{0.0}")], mode="vline")
    )
    return p


# ---------------------------------------------------------------------------
# Node history figure
# ---------------------------------------------------------------------------

def make_node_figure(
    node_df: pd.DataFrame,
    fire_df: pd.DataFrame,
    node_id: Optional[int],
    temp_unit: str = "C",
) -> figure:
    """Temperature-vs-time chart for a single node (+ optional fire curve).

    Parameters
    ----------
    node_df:
        DataFrame with columns ``time``, ``Temperature``.
    fire_df:
        DataFrame with columns ``time``, ``temperature``.
    node_id:
        Node identifier (used in the chart title).
    temp_unit:
        ``"C"`` or ``"F"``.
    """
    title = f"Node {node_id} – Temperature History" if node_id is not None else "Node Temperature History"
    p = figure(
        width=700,
        height=420,
        title=title,
        toolbar_location="above",
        tools="pan,wheel_zoom,box_zoom,reset,hover,save",
        x_axis_label="Time (s)",
        y_axis_label=f"Temperature (°{temp_unit})",
    )
    p.background_fill_color = "white"

    if node_id is None or node_df.empty:
        return p

    y_node = node_df["Temperature"].to_numpy()
    if temp_unit == "F":
        y_node = _c_to_f(y_node)

    node_source = ColumnDataSource(dict(x=node_df["time"], y=y_node))
    r1 = p.line("x", "y", source=node_source, line_color="#c91919", line_width=2, legend_label=f"Node {node_id}")
    p.scatter("x", "y", source=node_source, size=4, color="#c91919")

    if not fire_df.empty and "time" in fire_df.columns and "temperature" in fire_df.columns:
        y_fire = fire_df["temperature"].to_numpy()
        if temp_unit == "F":
            y_fire = _c_to_f(y_fire)
        fire_source = ColumnDataSource(dict(x=fire_df["time"], y=y_fire))
        p.line(
            "x", "y",
            source=fire_source,
            line_color="#ff7f0e",
            line_dash="dashed",
            line_width=2,
            legend_label="Fire Curve",
        )

    p.legend.click_policy = "hide"
    p.legend.location = "top_left"
    p.add_tools(
        HoverTool(
            tooltips=[("Time", "@x{0.0} s"), ("Temp", "@y{0.1} °" + temp_unit)],
            mode="vline",
        )
    )
    return p
