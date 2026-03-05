"""
shared.visualization.color_schemes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Shared colour palettes and themes for SAFIR result visualisations.

All palettes are plain Python lists/dicts so they work with Bokeh,
Plotly, Matplotlib, or any other rendering backend.
"""

# ---------------------------------------------------------------------------
# Material colours – one colour per material index (cyclic)
# ---------------------------------------------------------------------------

MATERIAL_COLORS: list[str] = [
    "#1f77b4",  # steel-blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # grey
    "#bcbd22",  # olive
    "#17becf",  # cyan
]


def get_material_color(material_index: int) -> str:
    """Return a colour string for *material_index* (cyclic)."""
    return MATERIAL_COLORS[material_index % len(MATERIAL_COLORS)]


# ---------------------------------------------------------------------------
# Temperature palette (cool → warm, 11 stops)
# ---------------------------------------------------------------------------

TEMPERATURE_PALETTE: list[str] = [
    "#313695",
    "#4575b4",
    "#74add1",
    "#abd9e9",
    "#e0f3f8",
    "#ffffbf",
    "#fee090",
    "#fdae61",
    "#f46d43",
    "#d73027",
    "#a50026",
]
"""Blue-to-red diverging palette suitable for temperature maps."""


# ---------------------------------------------------------------------------
# Default line colours for sequential time-series plots
# ---------------------------------------------------------------------------

DEFAULT_LINE_COLORS: list[str] = [
    "blue",
    "green",
    "red",
    "purple",
    "orange",
    "brown",
    "teal",
    "maroon",
]
