import sqlite3
import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.models import TextInput, ColumnDataSource, Button, HoverTool, Div
from bokeh.layouts import column, row
import base64

# === USER SETTINGS ===
DB_PATH = "S2A.db"  # <-- Change to your database file
DEFAULT_NODE_ID = 419           # <-- Default node to show

# === Bokeh data source ===
source = ColumnDataSource(data=dict(TimeStep=[], D1=[], D2=[], D3=[]))

# === Widgets ===
node_input = TextInput(title="Enter Node ID", value=str(DEFAULT_NODE_ID))
export_button = Button(label="Export CSV", button_type="success")

# === Plot ===
p = figure(
    title="Node Displacement vs Time",
    x_axis_label="Time (s)",
    y_axis_label="Displacement (m)",
    tools="pan,wheel_zoom,box_zoom,reset,save",
    width=900,
    height=500
)
hover = HoverTool(tooltips=[("Time", "@TimeStep"), ("Displacement", "$y")])
p.add_tools(hover)

p.line("TimeStep", "D1", source=source, color="red", line_width=2, legend_label="D1")
p.line("TimeStep", "D2", source=source, color="green", line_width=2, legend_label="D2")
p.line("TimeStep", "D3", source=source, color="blue", line_width=2, legend_label="D3")

p.legend.click_policy = "hide"

# === Functions ===
def load_displacement_data(node_id):
    """Load displacement time history for a node."""
    conn = sqlite3.connect(DB_PATH)
    timestamps_df = pd.read_sql("SELECT id AS timestamp_id, time AS TimeStep FROM timestamps", conn)
    disp_df = pd.read_sql(f"""
        SELECT timestamp_id, node_id, D1, D2, D3
        FROM node_displacements
        WHERE node_id = {node_id}
    """, conn)
    conn.close()

    if disp_df.empty:
        return pd.DataFrame(columns=["TimeStep", "D1", "D2", "D3"])

    disp_df = disp_df.merge(timestamps_df, on="timestamp_id", how="left")
    disp_df = disp_df.sort_values("TimeStep")
    return disp_df[["TimeStep", "D1", "D2", "D3"]]

def update_plot(attr=None, old=None, new=None):
    """Update plot when node changes."""
    if node_input.value.strip().isdigit():
        node_id = int(node_input.value.strip())
        df = load_displacement_data(node_id)
        source.data = {
            "TimeStep": df["TimeStep"],
            "D1": df["D1"],
            "D2": df["D2"],
            "D3": df["D3"]
        }
        p.title.text = f"Node {node_id} Displacement vs Time"

def export_csv():
    """Export current data as CSV."""
    if not source.data["TimeStep"]:
        return
    df = pd.DataFrame(source.data)
    csv_bytes = df.to_csv(index=False).encode()
    b64 = base64.b64encode(csv_bytes).decode()
    download_link = Div(
        text=f'<a href="data:text/csv;base64,{b64}" download="node_displacement.csv">Download CSV</a>'
    )
    curdoc().add_root(download_link)

# === Callbacks ===
node_input.on_change("value", update_plot)
export_button.on_click(export_csv)

# === Initial Load ===
update_plot()

# === Layout ===
layout = column(
    row(node_input, export_button),
    p
)

curdoc().add_root(layout)
curdoc().title = "Node Displacement Viewer"
