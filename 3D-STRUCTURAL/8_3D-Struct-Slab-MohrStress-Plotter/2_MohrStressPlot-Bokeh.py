# StressPlotterServer.py
# Run:
#   bokeh serve --show StressPlotterServer.py --args path/to/your.db [tensor|principal]
#
# If method is omitted, the app will auto-pick the first available.

import sys, os, sqlite3
import numpy as np
import pandas as pd
from bokeh.io import curdoc
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource, Slider, Select, Div, CheckboxGroup
from bokeh.plotting import figure

TBL = "nodal_principal_stress"   # expects: timestamp_id,node_id,method,sigma1,sigma2,theta_rad,x,y,z

# ---------- data helpers ----------
def db_exists(p): return os.path.isfile(p)

def fetch_methods(con):
    try:
        df = pd.read_sql_query(f"SELECT DISTINCT method FROM {TBL} ORDER BY method", con)
        return [m for m in df["method"].dropna().astype(str).tolist()]
    except Exception:
        return []

def fetch_steps(con, method):
    q = f"SELECT DISTINCT timestamp_id FROM {TBL} WHERE method=? ORDER BY timestamp_id"
    df = pd.read_sql_query(q, con, params=[method])
    return df["timestamp_id"].dropna().astype(int).tolist()

def load_step(con, ts, method):
    q = f"""
        SELECT x, y, sigma1, sigma2, theta_rad
        FROM {TBL}
        WHERE timestamp_id=? AND method=?
    """
    df = pd.read_sql_query(q, con, params=[int(ts), method])
    # sanitize
    for c in ("x","y","sigma1","sigma2","theta_rad"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna()

def build_sources(df, scale=None, rescale=False):
    """Return (src1, src2, scale). Keep prior scale unless rescale=True or None."""
    if df.empty:
        empty = ColumnDataSource(dict(x0=[], y0=[], x1=[], y1=[]))
        return empty, empty, 1.0
    x = df["x"].to_numpy(); y = df["y"].to_numpy()
    th = df["theta_rad"].to_numpy()
    s1 = df["sigma1"].to_numpy(); s2 = df["sigma2"].to_numpy()

    if rescale or scale is None:
        mags = np.concatenate([np.abs(s1), np.abs(s2)])
        mags = mags[mags > 0]
        s_ref = np.percentile(mags, 95) if mags.size else 1.0
        span = max(float(df["x"].max() - df["x"].min()),
                   float(df["y"].max() - df["y"].min()), 1.0)
        scale = 0.05 * span / s_ref

    # σ1: along theta
    dx1 = scale * s1 * np.cos(th); dy1 = scale * s1 * np.sin(th)
    src1 = ColumnDataSource(dict(x0=x-0.5*dx1, y0=y-0.5*dy1, x1=x+0.5*dx1, y1=y+0.5*dy1))

    # σ2: perpendicular
    th2 = th + np.pi/2.0
    dx2 = scale * s2 * np.cos(th2); dy2 = scale * s2 * np.sin(th2)
    src2 = ColumnDataSource(dict(x0=x-0.5*dx2, y0=y-0.5*dy2, x1=x+0.5*dx2, y1=y+0.5*dy2))

    return src1, src2, scale

# ---------- app ----------
def main(doc, db_path, preferred_method=None):
    status = Div(text="", width=420)
    if not db_exists(db_path):
        doc.add_root(Div(text=f"<b>Error:</b> DB not found at <code>{db_path}</code>"))
        return

    try:
        con = sqlite3.connect(db_path)
    except Exception as e:
        doc.add_root(Div(text=f"<b>Error opening DB:</b> {e}")); return

    # check table
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if TBL not in tables:
        doc.add_root(Div(text=f"<b>Error:</b> Table <code>{TBL}</code> not found in DB.")); return

    methods = fetch_methods(con)
    if not methods:
        doc.add_root(Div(text=f"<b>Error:</b> No methods found in <code>{TBL}</code>.")); return

    method = preferred_method if (preferred_method in methods) else methods[0]
    if preferred_method and preferred_method not in methods:
        status.text += f"⚠️ Method '{preferred_method}' not present; using '{method}'.<br>"

    step_ids = fetch_steps(con, method)
    if not step_ids:
        doc.add_root(Div(text=f"<b>Error:</b> No timesteps for method <code>{method}</code>.")); return

        # initial data
    idx = 0
    df0 = load_step(con, step_ids[idx], method)
    src1, src2, scale0 = build_sources(df0, scale=None, rescale=True)
    scale_ref = {"value": scale0}  # mutable container so callbacks can update

    # figure
    fig = figure(width=950, height=720, match_aspect=True,
                 title=f"Principal Stresses — timestep {step_ids[idx]}, method={method}",
                 tools="pan,wheel_zoom,reset,save")
    fig.xaxis.axis_label = "X"
    fig.yaxis.axis_label = "Y"

    # σ1 in blue
    r1 = fig.segment("x0", "y0", "x1", "y1",
                     source=src1,
                     line_width=1.6,
                     line_alpha=0.95,
                     line_color="blue")

    # σ2 in red
    r2 = fig.segment("x0", "y0", "x1", "y1",
                     source=src2,
                     line_width=1.6,
                     line_alpha=0.95,
                     line_color="red")

    # controls
    lbl = Div(text=f"<b>timestep_id = {step_ids[idx]}</b>")
    slider = Slider(title="Timestep index", start=0, end=len(step_ids) - 1, step=1, value=idx)
    method_sel = Select(title="Method", options=methods, value=method)
    toggles = CheckboxGroup(labels=["Show σ₁", "Show σ₂", "Rescale each step"], active=[0, 1])
    status = Div(text="", width=420)

    def refresh(ts, meth, force_rescale=False):
        df = load_step(con, ts, meth)
        rescale_flag = (2 in toggles.active) or force_rescale
        s1, s2, new_scale = build_sources(
            df,
            scale=None if rescale_flag else scale_ref["value"],
            rescale=rescale_flag
        )

        # ✅ Bokeh requires a *plain dict* when setting .data
        src1.data = dict(s1.data)
        src2.data = dict(s2.data)

        if rescale_flag:
            scale_ref["value"] = new_scale

        fig.title.text = f"Principal Stresses — timestep {ts}, method={meth}"
        lbl.text = f"<b>timestep_id = {ts}</b>"
        status.text = f"nodes plotted: {len(df)} | scale: {scale_ref['value']:.4g}"

    def on_slider(attr, old, new):
        ts = step_ids[slider.value]
        refresh(ts, method_sel.value)

    def on_method(attr, old, new):
        nonlocal_steps = fetch_steps(con, method_sel.value)
        if not nonlocal_steps:
            status.text = f"⚠️ No steps for method '{method_sel.value}'."
            src1.data = dict(x0=[], y0=[], x1=[], y1=[]);
            src2.data = dict(x0=[], y0=[], x1=[], y1=[])
            return
        # update available step list
        step_ids.clear()
        step_ids.extend(nonlocal_steps)
        slider.update(end=len(step_ids) - 1, value=0)
        refresh(step_ids[0], method_sel.value, force_rescale=True)

    def on_toggles(attr, old, new):
        r1.visible = 0 in toggles.active
        r2.visible = 1 in toggles.active
        if 2 in toggles.active:
            refresh(step_ids[slider.value], method_sel.value, force_rescale=True)

    slider.on_change("value", on_slider)
    method_sel.on_change("value", on_method)
    toggles.on_change("active", on_toggles)

    controls = column(method_sel, lbl, slider, toggles, status, width=420)
    doc.add_root(row(controls, fig, sizing_mode="stretch_both"))

    doc.on_session_destroyed(lambda _: con.close())

# ----- entrypoint (Bokeh passes args via --args) -----
args = sys.argv[1:]
if "--args" in args:
    args = args[args.index("--args")+1:]
db_path = args[0] if len(args) >= 1 else "S2A-9_Bays.db"
method_in = args[1] if len(args) >= 2 else None
main(curdoc(), db_path, method_in)
