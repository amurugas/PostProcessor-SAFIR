import sqlite3
import pandas as pd
from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, Div, Select
from bokeh.layouts import column
from bokeh.plotting import figure

# === UNIT CONVERSION FACTORS ===
FORCE_N_TO_KIP = 1 / 4448.22
MOMENT_NM_TO_KIPIN = 1 / 112.985  # ~8.85075

# === DATABASE SETUP ===
db_path = "S2A-1.db"
try:
    conn = sqlite3.connect(db_path)
    print("✅ Connected to database")

    df_forces = pd.read_sql_query("SELECT * FROM beam_forces WHERE gauss_point = 1", conn)
    df_nodes = pd.read_sql_query("SELECT DISTINCT beam_id, beam_tag FROM beam_nodes", conn)
    df_sections = pd.read_sql_query("SELECT beam_tag, section FROM beam_section", conn)
    df_time = pd.read_sql_query("SELECT id AS timestamp_id, time FROM timestamps", conn)

    # Merge data
    merged = pd.merge(df_forces, df_nodes, on='beam_id', how='left')
    merged = pd.merge(merged, df_time, on='timestamp_id', how='left')
    merged = pd.merge(merged, df_sections, on='beam_tag', how='left')  # Add section info

    merged['beam_id'] = merged['beam_id'].astype(int)

    print(f"📊 Merged dataset shape: {merged.shape}")
    print(f"📊 Available beam_ids: {sorted(merged['beam_id'].unique())[:10]}...")

except Exception as e:
    print(f"❌ Database error: {e}")
    merged = pd.DataFrame()

# === FORCE COMPONENTS TO PLOT (converted units) ===
force_columns = ['N', 'Vy', 'Vz', 'My', 'Mz']
force_units = {
    'N': 'Axial Force (kips)',
    'Vy': 'Shear Y (kips)',
    'Vz': 'Shear Z (kips)',
    'My': 'Moment Y (kip-in)',
    'Mz': 'Moment Z (kip-in)'
}

conversion_factors = {
    'N': FORCE_N_TO_KIP,
    'Vy': FORCE_N_TO_KIP,
    'Vz': FORCE_N_TO_KIP,
    'My': MOMENT_NM_TO_KIPIN,
    'Mz': MOMENT_NM_TO_KIPIN
}

# === DATA SOURCES AND PLOTS ===
sources = {col: ColumnDataSource(data={'Time': [], 'Force': []}) for col in force_columns}
plots = []

for col in force_columns:
    p = figure(height=250, width=800,
               title=f"{force_units[col]} vs Time (Beam ID: -)",
               x_axis_label='Time (s)', y_axis_label=force_units[col],
               tools="pan,wheel_zoom,box_zoom,reset")
    p.line('Time', 'Force', source=sources[col], line_width=2, color='blue', alpha=0.8)
    plots.append(p)

# === WIDGETS ===
if not merged.empty:
    beam_id_options = [str(i) for i in sorted(merged['beam_id'].unique())]
else:
    beam_id_options = ["No data"]

beam_id_input = Select(title="Select Beam ID:", value=beam_id_options[0], options=beam_id_options)
status_display = Div(text="", styles={"font-size": "12px", "margin": "10px", "color": "blue"})

# === UPDATE FUNCTION ===
def update_data(attr, old, new):
    beam_id = beam_id_input.value
    print(f"\n🔄 Selected beam: {beam_id}")

    try:
        beam_id_int = int(beam_id)
        data = merged[merged['beam_id'] == beam_id_int].copy()

        if data.empty:
            for col in force_columns:
                sources[col].data = {'Time': [], 'Force': []}
            status_display.text = f"<b>No data found for beam ID:</b> {beam_id}"
            return

        data = data.sort_values('time')
        time_data = data['time'].tolist()

        section_value = data['section'].iloc[0] if 'section' in data.columns else "?"

        for col in force_columns:
            if col in data.columns:
                # SAFELY CONVERT and APPLY conversion
                force_series = pd.to_numeric(data[col], errors='coerce')
                converted = (force_series * conversion_factors[col]).fillna(0).tolist()
                sources[col].data = {'Time': time_data, 'Force': converted}
                print(f"✅ Converted '{col}': {converted[:3]}...")
            else:
                sources[col].data = {'Time': [], 'Force': []}
                print(f"⚠️ Column '{col}' missing")

        status_display.text = (
            f"<b>Beam {beam_id}:</b> {len(time_data)} time steps | "
            f"<b>Section:</b> {section_value}"
        )

        for p in plots:
            col_label = p.yaxis.axis_label
            p.title.text = f"{col_label} vs Time (Beam ID: {beam_id})"

    except Exception as e:
        print(f"❌ Error processing beam {beam_id}: {e}")
        for col in force_columns:
            sources[col].data = {'Time': [], 'Force': []}
        status_display.text = f"<b>Error:</b> {str(e)}"


beam_id_input.on_change('value', update_data)

# === LAYOUT ===
layout = column(
    beam_id_input,
    status_display,
    *plots
)

curdoc().add_root(layout)
curdoc().title = "Beam Force Viewer (kips/inches)"

# === INITIAL LOAD ===
print("\n🚀 Initializing...")
update_data(None, None, None)
print("🏁 Ready")
