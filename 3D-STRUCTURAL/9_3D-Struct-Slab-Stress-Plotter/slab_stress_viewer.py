
import argparse
import sqlite3
import pandas as pd
import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (ColumnDataSource, ColorBar, LinearColorMapper, BasicTicker, 
                          PrintfTickFormatter, HoverTool, Select, Slider, CheckboxGroup, 
                          Div)
from bokeh.plotting import figure

# -------------------------
# Args
# -------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--db", dest="db_path", default=None)
args, unknown = parser.parse_known_args()

if args.db_path is None and len(unknown) > 0 and unknown[0] not in ('--session-ids',):
    # allow bare path passed without --db
    args.db_path = unknown[0]

if args.db_path is None:
    msg = Div(text=(
        "<b>Missing database path.</b><br>"
        "Start the app like:<br>"
        "<code>bokeh serve --show slab_stress_viewer.py --args path/to/your.db</code>"
    ), width=600)
    curdoc().add_root(msg)
    raise SystemExit

# -------------------------
# Load data
# -------------------------
con = sqlite3.connect(args.db_path)

# shell_nodes
shell_nodes = pd.read_sql_query("SELECT shell_id, N1, N2, N3, N4, COALESCE(shell_tag, '') AS shell_tag FROM shell_nodes", con)

# node_coordinates
nodes = pd.read_sql_query("SELECT node_id, x, y, z FROM node_coordinates", con)

# shell_strains
strains = pd.read_sql_query(
    "SELECT id, timestamp_id, shell_id, integration_point, thickness, "
    "Sx, Sy, Sz, Px, Py, Pz, Dx, Dy, Dz "
    "FROM shell_strains", con)

con.close()

if shell_nodes.empty or nodes.empty or strains.empty:
    msg = Div(text="<b>One or more required tables are empty.</b> Make sure the DB has data.", width=600)
    curdoc().add_root(msg)
    raise SystemExit

# -------------------------
# Build shell polygons (plan view XY)
# -------------------------
# Map node_id -> (x, y, z)
node_map = nodes.set_index('node_id')[['x', 'y', 'z']]

def row_to_xy(row):
    ids = [row['N1'], row['N2'], row['N3'], row['N4']]
    pts = node_map.loc[ids]
    xs = pts['x'].values.tolist() + [pts['x'].values.tolist()[0]]  # close polygon
    ys = pts['y'].values.tolist() + [pts['y'].values.tolist()[0]]
    return xs, ys

xy = shell_nodes.apply(row_to_xy, axis=1, result_type='expand')
xy.columns = ['xs', 'ys']
shell_poly = pd.concat([shell_nodes.reset_index(drop=True), xy], axis=1)

# -------------------------
# Widgets
# -------------------------
stress_options = ['Sx', 'Sy', 'Sz', 'Px', 'Py', 'Pz', 'Dx', 'Dy', 'Dz']
w_comp = Select(title="Component", value='Sx', options=stress_options)

timestamps = sorted(strains['timestamp_id'].unique().tolist())
w_time = Select(title="timestamp_id", value=str(timestamps[0]), options=[str(t) for t in timestamps])

thicks = sorted(strains['thickness'].unique().tolist())
w_thick = Select(title="thickness (NGT)", value=str(thicks[0]), options=[str(t) for t in thicks])

ips = sorted(strains['integration_point'].unique().tolist())
w_ip = Select(title="integration_point (NGA)", value=str(ips[0]), options=[str(i) for i in ips])

w_alpha = Slider(title="Fill alpha", start=0.2, end=1.0, step=0.05, value=0.9)
w_edges = CheckboxGroup(labels=["Show mesh edges"], active=[0])

# -------------------------
# DataSource + Figure
# -------------------------
source = ColumnDataSource(data=dict(xs=[], ys=[], value=[], shell_id=[], shell_tag=[]))

p = figure(title="Slab Stress Viewer (plan view)", match_aspect=True, tools="pan,wheel_zoom,reset,save",
           x_axis_label="X", y_axis_label="Y")
mapper = LinearColorMapper(palette="Turbo256", low=0, high=1)

patches = p.patches('xs', 'ys', source=source, line_color='black', line_alpha=0.4,
                    fill_color={'field':'value','transform':mapper}, fill_alpha=w_alpha.value)

color_bar = ColorBar(color_mapper=mapper, ticker=BasicTicker(desired_num_ticks=10),
                     formatter=PrintfTickFormatter(format="%.3f"), label_standoff=8, location=(0,0))
p.add_layout(color_bar, 'right')

hover = HoverTool(tooltips=[
    ("shell_id", "@shell_id"),
    ("shell_tag", "@shell_tag"),
    (f"value ({w_comp.value})", "@value{0.000}"),
])
p.add_tools(hover)

# -------------------------
# Update function
# -------------------------
def update():
    comp = w_comp.value
    ts = int(w_time.value)
    ngt = int(w_thick.value)
    nga = int(w_ip.value)

    df = strains[(strains['timestamp_id'] == ts) &
                 (strains['thickness'] == ngt) &
                 (strains['integration_point'] == nga)][['shell_id', comp]].rename(columns={comp: 'value'})
    merged = shell_poly.merge(df, on='shell_id', how='left')
    v = merged['value'].astype(float)
    # Robust color limits
    finite = v.replace([np.inf, -np.inf], np.nan).dropna()
    if finite.empty:
        low, high = 0.0, 1.0
    else:
        q1, q99 = np.quantile(finite, [0.01, 0.99])
        if q1 == q99:
            low, high = float(finite.min()), float(finite.max() + 1e-9)
        else:
            low, high = float(q1), float(q99)

    mapper.low = low
    mapper.high = high

    source.data = dict(
        xs=merged['xs'].tolist(),
        ys=merged['ys'].tolist(),
        value=v.fillna(np.nan).tolist(),
        shell_id=merged['shell_id'].tolist(),
        shell_tag=merged['shell_tag'].tolist(),
    )

    patches.glyph.fill_alpha = w_alpha.value
    patches.glyph.line_alpha = 0.6 if 0 in w_edges.active else 0.0
    hover.tooltips = [
        ("shell_id", "@shell_id"),
        ("shell_tag", "@shell_tag"),
        (f"value ({comp})", "@value{0.000}"),
    ]
    p.title.text = f"Slab Stress Viewer — {comp} at t={ts}, NGT={ngt}, NGA={nga}  (local shell axes)"

for w in (w_comp, w_time, w_thick, w_ip, w_alpha, w_edges):
    w.on_change('value' if hasattr(w, 'value') else 'active', lambda attr, old, new: update())

update()

curdoc().add_root(column(
    Div(text="<b>SQLite:</b> " + args.db_path),
    row(w_comp, w_time, w_thick, w_ip),
    row(w_alpha, w_edges),
    p
))
curdoc().title = "Slab Stress Viewer"


