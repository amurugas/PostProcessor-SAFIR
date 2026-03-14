from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource, Slider, RangeSlider, CrosshairTool, HoverTool, LabelSet, Div, TextInput
from bokeh.layouts import column, row
import sqlite3
import numpy as np

# === CONSTANTS ===
DB_PATH = "BatchXml/Beams/w14x22_F.db"
N_TO_KIPS = 1 / 4448.22
NM_TO_KIPS_FT = 1 / (4448.22 * 0.3048)
M_TO_INCHES = 39.3701

# === HEADER ===
db_path_header = Div(text=f"<h1 style='text-align: center; color: black;'>{DB_PATH}</h1>")

# === DATABASE HELPERS ===
def run_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

def get_limits(query, scale_factors):
    results = run_query(query)[0]
    return tuple(min_max * scale for min_max, scale in zip(zip(results[::2], results[1::2]), scale_factors))

# === DATA FETCHING ===
def get_all_times():
    return [row[0] for row in run_query("SELECT DISTINCT time FROM timestamps ORDER BY time")]

def get_closest_time(time):
    result = run_query("SELECT MAX(time) FROM timestamps WHERE time <= ?", (time,))[0][0]
    return result if result is not None else 31.0


# === INITIAL DATA ===
times = [int(round(t)) for t in get_all_times()]
initial_time = 20

n_limits, mz_limits, vz_limits = get_limits(
    "SELECT MIN(f.n), MAX(f.n), MIN(f.mz), MAX(f.mz), MIN(f.vz), MAX(f.vz) FROM forces f",
    (N_TO_KIPS, N_TO_KIPS, NM_TO_KIPS_FT, NM_TO_KIPS_FT, N_TO_KIPS, N_TO_KIPS)
)

dx_limits, dy_limits, dz_limits = get_limits(
    "SELECT MIN(d.dx), MAX(d.dx), MIN(d.dy), MAX(d.dy), MIN(d.dz), MAX(d.dz) FROM displacements d",
    (M_TO_INCHES, M_TO_INCHES, M_TO_INCHES, M_TO_INCHES, 1, 1)
)

beam_ids, n, mz, vz, _ = get_forces_for_time(initial_time)
node_ids, x_coords, dx, dy, dz, _ = get_displacements_for_time(initial_time)

fire_time, fire_temp = get_fire_curve_data()
material_avg_temps = fetch_average_temperatures()

# === SOURCES ===
force_source = ColumnDataSource(data={
    'beam_ids': beam_ids,
    'N': n,
    'Mz': mz,
    'Vz': vz,
    'N_formatted': [f"{v:.2f}" for v in n],
    'Mz_formatted': [f"{v:.2f}" for v in mz],
    'Vz_formatted': [f"{v:.2f}" for v in vz],
})

disp_source = ColumnDataSource(data={
    'node_ids': node_ids,
    'x_coords': x_coords,
    'dx': dx,
    'dy': dy,
    'dz': dz,
    'dx_formatted': [f"{v:.3f}" for v in dx],
    'dy_formatted': [f"{v:.3f}" for v in dy],
    'dz_formatted': [f"{v:.3f}" for v in dz],
})

fire_source = ColumnDataSource(data={"time": fire_time, "temperature": fire_temp})
highlight_source = ColumnDataSource(data={"time": [fire_time[0]], "temperature": [fire_temp[0]]})

avg_temp_sources = {
    mat_id: ColumnDataSource(data=data) for mat_id, data in material_avg_temps.items()
}

# === PLOTS ===
def create_labeled_plot(x, y, y_fmt, color, title, ylabel, y_range, source):
    plot = figure(title=title, x_axis_label=x, y_axis_label=ylabel, y_range=y_range, tools="")
    plot.line(x, y, source=source, line_width=2, color=color)
    labels = LabelSet(x=x, y=y, text=y_fmt, level='overlay', source=source,
                      text_align='center', text_baseline='bottom',
                      text_font_size="8pt", text_color=color)
    plot.add_layout(labels)
    plot.add_tools(CrosshairTool(dimensions="both"), HoverTool(tooltips=[("Index", "$index"), ("Value", "$y")]))
    return plot

def create_force_plots():
    return {
        'N': create_labeled_plot('beam_ids', 'N', 'N_formatted', 'blue', 'Axial Force (kips)', 'Axial Force (kips)', n_limits, force_source),
        'Mz': create_labeled_plot('beam_ids', 'Mz', 'Mz_formatted', 'green', 'Moment (kips-ft)', 'Moment (kips-ft)', mz_limits, force_source),
        'Vz': create_labeled_plot('beam_ids', 'Vz', 'Vz_formatted', 'red', 'Shear Force (kips)', 'Shear Force (kips)', vz_limits, force_source),
    }

def create_disp_plots():
    plots = {}
    for d, df, color, title, ylabel, lim in zip(
        ['dx', 'dy', 'dz'], ['dx_formatted', 'dy_formatted', 'dz_formatted'],
        ['purple', 'orange', 'brown'],
        ['Displacement X', 'Displacement Y', 'Displacement Z'],
        ['dx (inches)', 'dy (inches)', 'dz (radians)'],
        [dx_limits, dy_limits, dz_limits]
    ):
        plot = figure(title=title, x_axis_label="X Coord", y_axis_label=ylabel, y_range=lim, tools="")
        plot.scatter('x_coords', d, source=disp_source, size=8, color=color, fill_alpha=0.6)
        labels = LabelSet(x='x_coords', y=d, text=df, level='overlay', source=disp_source,
                          text_align='center', text_baseline='bottom',
                          text_font_size="8pt", text_color=color)
        plot.add_layout(labels)
        plot.add_tools(CrosshairTool(dimensions="both"), HoverTool(tooltips=[("Node ID", "$index"), ("Value", "$y")]))
        plots[d] = plot
    return plots

def create_fire_curve_plot():
    plot = figure(title="Fire Time-Temperature Curve", x_axis_label="Time", y_axis_label="Temperature (°C)", tools="")
    plot.line("time", "temperature", source=fire_source, line_width=2, color="orange")
    plot.scatter("time", "temperature", source=highlight_source, size=10, color="red")
    plot.legend.location = "top_right"
    return plot

def create_avg_temp_plot():
    plot = figure(title="Average Temperature by Material", x_axis_label="Time", y_axis_label="Avg Temp (°C)", tools="")
    for mat_id, source in avg_temp_sources.items():
        plot.line('timestamps', 'avg_temps', source=source, line_width=2, legend_label=f"Material {mat_id}")
    plot.legend.title = "Materials"
    plot.legend.location = "top_right"
    plot.legend.click_policy = "hide"
    return plot

# === CALLBACKS ===
def update_plots(attr, old, new):
    time = time_slider.value
    node_range = node_range_slider.value
    beam_ids, n, mz, vz, _ = get_forces_for_time(time)
    node_ids, x, dx, dy, dz, _ = get_displacements_for_time(time)
    mask = (node_ids >= node_range[0]) & (node_ids <= node_range[1])
    force_source.data = {
        'beam_ids': beam_ids, 'N': n, 'Mz': mz, 'Vz': vz,
        'N_formatted': [f"{v:.2f}" for v in n],
        'Mz_formatted': [f"{v:.2f}" for v in mz],
        'Vz_formatted': [f"{v:.2f}" for v in vz],
    }
    disp_source.data = {
        'node_ids': node_ids[mask], 'x_coords': x[mask], 'dx': dx[mask], 'dy': dy[mask], 'dz': dz[mask],
        'dx_formatted': [f"{v:.3f}" for v in dx[mask]],
        'dy_formatted': [f"{v:.3f}" for v in dy[mask]],
        'dz_formatted': [f"{v:.3f}" for v in dz[mask]],
    }

def update_fire_plot_highlight(time):
    idx = np.abs(np.array(fire_source.data['time']) - time).argmin()
    t = fire_source.data['time'][idx]
    temp = fire_source.data['temperature'][idx]
    highlight_source.data = {"time": [t], "temperature": [temp]}
    temp_div.text = f"<h2>Fire Curve Temp at Selected Time: {temp:.2f} °C</h2>"

def update_time_from_input(attr, old, new):
    try:
        val = int(text_input_time.value)
        if val < min(times) or val > max(times):
            raise ValueError
        time_slider.value = val
    except ValueError:
        text_input_time.value = f"Invalid input. Enter a time between {min(times)} and {max(times)}."

# === UI ===
time_slider = Slider(start=min(times), end=max(times), value=initial_time, step=1, title="Time")
time_slider.on_change('value', lambda attr, old, new: (update_plots(attr, old, new), update_fire_plot_highlight(new)))

text_input_time = TextInput(value=str(initial_time), title="Enter Time:")
text_input_time.on_change('value', update_time_from_input)

temp_div = Div(text=f"<h2>Temperature at Selected Time: {fire_temp[0]:.2f} °C</h2>")

node_range_slider = RangeSlider(start=min(node_ids), end=max(node_ids), value=(1, 21), step=1, title="Node Range")
node_range_slider.on_change('value', update_plots)

# === LAYOUT ===
layout = column(
    db_path_header, temp_div, time_slider, text_input_time, node_range_slider,
    row(*create_force_plots().values()),
    row(*create_disp_plots().values()),
    row(create_fire_curve_plot(), create_avg_temp_plot())
)

curdoc().add_root(layout)
curdoc().title = "2D Results Viewer"
