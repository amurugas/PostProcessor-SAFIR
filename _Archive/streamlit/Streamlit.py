import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import tempfile
import io

st.set_page_config(page_title="SAFIR Results Dashboard", layout="wide")
st.title("🔥 SAFIR Results Dashboard")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload SAFIR SQLite Database (.db)", type=["db"])
if uploaded_file is None:
    st.warning("Please upload a SAFIR .db file to continue.")
    st.stop()

# --- Save uploaded file once ---
with tempfile.NamedTemporaryFile(delete=False) as tmp:
    tmp.write(uploaded_file.getbuffer())
    DB_PATH = tmp.name

# --- Load Table Function ---
@st.cache_data
def load_table(db_path, table_name):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# --- Load Data ---
timestamps_df = load_table(DB_PATH, "timestamps")
node_disp_df = load_table(DB_PATH, "node_displacements")
beam_force_df = load_table(DB_PATH, "beam_forces")
temp_df = load_table(DB_PATH, "temperature_curve")

# --- Create Tabs ---
tab1, tab2, tab3 = st.tabs(["Node Displacement", "Beam Forces", "Temperature–Time"])

# --- TAB 1: Node Displacement ---
with tab1:
    st.subheader("Node Displacement vs Time")
    node_ids = sorted(node_disp_df["node_id"].unique())
    selected_nodes = st.multiselect("Select Node IDs", node_ids, default=node_ids[:1])
    dof_choice = st.selectbox("Select Degree of Freedom", ["D1", "D2", "D3", "D4", "D5", "D6", "D7"])

    fig = px.line(title=f"Node Displacement - {dof_choice}")
    export_df = pd.DataFrame()

    for node in selected_nodes:
        df_filtered = node_disp_df[node_disp_df["node_id"] == node]
        df_plot = pd.merge(df_filtered, timestamps_df, left_on="timestamp_id", right_on="id")
        fig.add_scatter(x=df_plot["time"], y=df_plot[dof_choice], mode="lines", name=f"Node {node}")

        df_plot_export = df_plot[["time", dof_choice]].copy()
        df_plot_export["node_id"] = node
        export_df = pd.concat([export_df, df_plot_export])

    st.plotly_chart(fig, use_container_width=True)

    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    st.download_button("Download CSV", data=csv_buffer.getvalue(),
                       file_name="node_displacement.csv", mime="text/csv")

# --- TAB 2: Beam Forces ---
with tab2:
    st.subheader("Beam Forces vs Time")
    beam_ids = sorted(beam_force_df["beam_id"].unique())
    selected_beams = st.multiselect("Select Beam IDs", beam_ids, default=beam_ids[:1])
    force_types = ["N", "Mz", "My", "Mw", "Mr2", "Vz", "Vy"]
    selected_force = st.selectbox("Select Force Type", force_types)

    fig = px.line(title=f"Beam Forces - {selected_force}")
    export_df = pd.DataFrame()

    for beam in selected_beams:
        df_filtered = beam_force_df[beam_force_df["beam_id"] == beam]
        df_plot = pd.merge(df_filtered, timestamps_df, left_on="timestamp_id", right_on="id")
        fig.add_scatter(x=df_plot["time"], y=df_plot[selected_force], mode="lines", name=f"Beam {beam}")

        df_plot_export = df_plot[["time", selected_force]].copy()
        df_plot_export["beam_id"] = beam
        export_df = pd.concat([export_df, df_plot_export])

    st.plotly_chart(fig, use_container_width=True)

    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    st.download_button("Download CSV", data=csv_buffer.getvalue(),
                       file_name="beam_forces.csv", mime="text/csv")

# --- TAB 3: Temperature–Time Curve ---
with tab3:
    st.subheader("Temperature–Time Curve")
    fig = px.line(temp_df, x="time", y="temperature", title="Temperature vs Time")
    st.plotly_chart(fig, use_container_width=True)

    csv_buffer = io.StringIO()
    temp_df.to_csv(csv_buffer, index=False)
    st.download_button("Download CSV", data=csv_buffer.getvalue(),
                       file_name="temperature_curve.csv", mime="text/csv")

st.markdown("---")
st.caption("SAFIR Dashboard built with Streamlit & Plotly")
