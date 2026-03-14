import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# Page setup
# ============================================================
st.set_page_config(page_title="SAFIR Dashboard - 2D Thermal", layout="wide")


# ============================================================
# Configuration
# ============================================================
DEFAULT_DB_DIR = Path(r"C:\Users\am1\PycharmProjects\PostProcessor-SAFIR")
DB_EXTENSIONS = {".db", ".sqlite", ".sqlite3"}
REQUIRED_TABLES = {"timestamps", "node_coordinates", "solid_mesh", "node_temperatures"}


# ============================================================
# Styling
# ============================================================
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .dashboard-title {
            font-size: 2.0rem;
            font-weight: 700;
            color: #c91919;
            margin-bottom: 0.6rem;
        }
        .panel {
            border: 1.5px solid #d84b4b;
            border-radius: 8px;
            padding: 0.6rem 0.8rem 0.5rem 0.8rem;
            background: #ffffff;
            margin-bottom: 0.9rem;
        }
        .metric-label {
            color: #666;
            font-size: 0.9rem;
        }
        .metric-value {
            font-size: 1.0rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()
st.markdown('<div class="dashboard-title">SAFIR DASHBOARD - 2D THERMAL</div>', unsafe_allow_html=True)


# ============================================================
# DB discovery and base helpers
# ============================================================
def find_db_files(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in DB_EXTENSIONS])


@st.cache_data(show_spinner=False)
def list_tables(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name",
            conn,
        )
        return df["name"].astype(str).tolist()
    finally:
        conn.close()


@st.cache_data(show_spinner=False)
def run_query(db_path: str, query: str, params: tuple = ()) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


@st.cache_data(show_spinner=False)
def get_db_summary(db_path: str) -> dict:
    tables = set(list_tables(db_path))
    return {
        "tables": sorted(tables),
        "has_required_tables": REQUIRED_TABLES.issubset(tables),
        "has_material_list": "material_list" in tables,
        "has_frontiers": "frontiers" in tables,
        "has_temperature_curve": "temperature_curve" in tables,
        "has_summary_view": "vw_material_temperature_summary" in tables,
    }


# ============================================================
# SQL bootstrap helpers
# ============================================================
VW_SOLID_NODES_SQL = """
DROP VIEW IF EXISTS vw_solid_nodes;

CREATE VIEW vw_solid_nodes AS
SELECT solid_id, material_tag, N1 AS node_id FROM solid_mesh
UNION ALL
SELECT solid_id, material_tag, N2 AS node_id FROM solid_mesh
UNION ALL
SELECT solid_id, material_tag, N3 AS node_id FROM solid_mesh
UNION ALL
SELECT solid_id, material_tag, N4 AS node_id FROM solid_mesh;
"""

VW_MATERIAL_TEMP_SQL = """
DROP VIEW IF EXISTS vw_material_temperature_summary;

CREATE VIEW vw_material_temperature_summary AS
WITH material_node_temp AS (
    SELECT DISTINCT
        vsn.material_tag,
        nt.timestamp_id,
        nt.node_id,
        nt.Temperature
    FROM vw_solid_nodes vsn
    JOIN node_temperatures nt
        ON vsn.node_id = nt.node_id
)
SELECT
    mnt.material_tag AS material_id,
    COALESCE(ml.material_name, CAST(mnt.material_tag AS TEXT)) AS material_section_lookup,
    ts.time AS timestep,
    AVG(mnt.Temperature) AS avg_temp_material,
    MAX(mnt.Temperature) AS max_temp_material
FROM material_node_temp mnt
JOIN timestamps ts
    ON mnt.timestamp_id = ts.id
LEFT JOIN material_list ml
    ON mnt.material_tag = ml.material_tag
GROUP BY
    mnt.material_tag,
    material_section_lookup,
    ts.time
ORDER BY
    ts.time,
    mnt.material_tag;
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_node_temperatures_timestamp_id ON node_temperatures(timestamp_id);
CREATE INDEX IF NOT EXISTS idx_node_temperatures_node_id ON node_temperatures(node_id);
CREATE INDEX IF NOT EXISTS idx_timestamps_time ON timestamps(time);
CREATE INDEX IF NOT EXISTS idx_node_coordinates_node_id ON node_coordinates(node_id);
CREATE INDEX IF NOT EXISTS idx_solid_mesh_solid_id ON solid_mesh(solid_id);
CREATE INDEX IF NOT EXISTS idx_solid_mesh_material_tag ON solid_mesh(material_tag);
"""


def execute_script(db_path: str, script: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# Query helpers
# ============================================================
@st.cache_data(show_spinner=False)
def get_time_steps(db_path: str) -> pd.DataFrame:
    return run_query(db_path, "SELECT id, time FROM timestamps ORDER BY time")


@st.cache_data(show_spinner=False)
def get_node_coordinates(db_path: str) -> pd.DataFrame:
    return run_query(db_path, "SELECT node_id, x, y FROM node_coordinates")


@st.cache_data(show_spinner=False)
def get_solid_mesh(db_path: str) -> pd.DataFrame:
    return run_query(db_path, "SELECT solid_id, N1, N2, N3, N4, material_tag FROM solid_mesh")


@st.cache_data(show_spinner=False)
def get_material_lookup(db_path: str) -> pd.DataFrame:
    tables = set(list_tables(db_path))
    if "material_list" not in tables:
        return pd.DataFrame(columns=["material_tag", "material_name"])
    return run_query(db_path, "SELECT material_tag, material_name FROM material_list")


@st.cache_data(show_spinner=False)
def get_frontiers(db_path: str) -> pd.DataFrame:
    tables = set(list_tables(db_path))
    if "frontiers" not in tables:
        return pd.DataFrame(columns=["solid_id", "face1", "face2", "face3", "face4"])
    return run_query(db_path, "SELECT solid_id, face1, face2, face3, face4 FROM frontiers")


@st.cache_data(show_spinner=False)
def get_section_temperatures(db_path: str, timestamp_id: int) -> pd.DataFrame:
    query = """
    SELECT node_id, Temperature
    FROM node_temperatures
    WHERE timestamp_id = ?
    """
    return run_query(db_path, query, (timestamp_id,))


@st.cache_data(show_spinner=False)
def get_node_history(db_path: str, node_id: int) -> pd.DataFrame:
    query = """
    SELECT ts.time, nt.Temperature
    FROM node_temperatures nt
    JOIN timestamps ts ON ts.id = nt.timestamp_id
    WHERE nt.node_id = ?
    ORDER BY ts.time
    """
    return run_query(db_path, query, (node_id,))


@st.cache_data(show_spinner=False)
def get_material_summary(db_path: str) -> pd.DataFrame:
    tables = set(list_tables(db_path))
    if "vw_material_temperature_summary" in tables:
        return run_query(db_path, "SELECT * FROM vw_material_temperature_summary ORDER BY timestep, material_id")

    fallback = """
    WITH solid_nodes AS (
        SELECT solid_id, material_tag, N1 AS node_id FROM solid_mesh
        UNION ALL
        SELECT solid_id, material_tag, N2 AS node_id FROM solid_mesh
        UNION ALL
        SELECT solid_id, material_tag, N3 AS node_id FROM solid_mesh
        UNION ALL
        SELECT solid_id, material_tag, N4 AS node_id FROM solid_mesh
    ),
    material_node_temp AS (
        SELECT DISTINCT
            sn.material_tag,
            nt.timestamp_id,
            nt.node_id,
            nt.Temperature
        FROM solid_nodes sn
        JOIN node_temperatures nt
            ON sn.node_id = nt.node_id
    )
    SELECT
        mnt.material_tag AS material_id,
        COALESCE(ml.material_name, CAST(mnt.material_tag AS TEXT)) AS material_section_lookup,
        ts.time AS timestep,
        AVG(mnt.Temperature) AS avg_temp_material,
        MAX(mnt.Temperature) AS max_temp_material
    FROM material_node_temp mnt
    JOIN timestamps ts
        ON mnt.timestamp_id = ts.id
    LEFT JOIN material_list ml
        ON mnt.material_tag = ml.material_tag
    GROUP BY
        mnt.material_tag,
        material_section_lookup,
        ts.time
    ORDER BY
        ts.time,
        mnt.material_tag
    """
    return run_query(db_path, fallback)


@st.cache_data(show_spinner=False)
def get_fire_curve(db_path: str) -> pd.DataFrame:
    tables = set(list_tables(db_path))
    if "temperature_curve" not in tables:
        return pd.DataFrame(columns=["time", "temperature"])
    return run_query(db_path, "SELECT time, temperature FROM temperature_curve ORDER BY time")


@st.cache_data(show_spinner=False)
def get_section_geometry_payload(db_path: str) -> dict:
    return {
        "coords": get_node_coordinates(db_path),
        "mesh": get_solid_mesh(db_path),
        "materials": get_material_lookup(db_path),
        "frontiers": get_frontiers(db_path),
    }


# ============================================================
# Plot helpers
# ============================================================
def c_to_f(values):
    return values * 9.0 / 5.0 + 32.0


MATERIAL_COLORS = [
    "rgba(31, 119, 180, 0.35)",
    "rgba(255, 127, 14, 0.35)",
    "rgba(44, 160, 44, 0.35)",
    "rgba(214, 39, 40, 0.35)",
    "rgba(148, 103, 189, 0.35)",
    "rgba(140, 86, 75, 0.35)",
    "rgba(227, 119, 194, 0.35)",
    "rgba(127, 127, 127, 0.35)",
]


def make_material_color_map(material_tags) -> dict[int, str]:
    tags = [int(t) for t in pd.Series(list(material_tags)).dropna().unique().tolist()]
    return {tag: MATERIAL_COLORS[i % len(MATERIAL_COLORS)] for i, tag in enumerate(sorted(tags))}


def draw_section_view(
    geometry: dict,
    temp_df: pd.DataFrame,
    show_temperature: bool,
    show_material: bool,
    show_boundary: bool,
    show_node_ids: bool,
    show_frontier: bool,
    temp_unit: str,
) -> go.Figure:
    coords = geometry["coords"].copy()
    mesh = geometry["mesh"].copy()
    materials = geometry["materials"].copy()
    frontiers = geometry["frontiers"].copy()

    coord_map = coords.set_index("node_id")[["x", "y"]].to_dict("index") if not coords.empty else {}
    temp_map = dict(zip(temp_df["node_id"], temp_df["Temperature"])) if not temp_df.empty else {}

    material_name_map = {}
    if not materials.empty and {"material_tag", "material_name"}.issubset(materials.columns):
        material_name_map = dict(zip(materials["material_tag"], materials["material_name"]))

    frontier_map = {}
    if not frontiers.empty and "solid_id" in frontiers.columns:
        frontier_map = frontiers.set_index("solid_id").to_dict("index")

    color_map = make_material_color_map(mesh["material_tag"].dropna().tolist()) if not mesh.empty else {}

    fig = go.Figure()

    for _, row in mesh.iterrows():
        solid_id = int(row["solid_id"])
        node_ids = [
            int(row[c])
            for c in ["N1", "N2", "N3", "N4"]
            if c in row and pd.notna(row[c]) and int(row[c]) in coord_map
        ]
        if len(node_ids) < 3:
            continue

        pts = [(coord_map[n]["x"], coord_map[n]["y"]) for n in node_ids]
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        material_tag = int(row["material_tag"]) if pd.notna(row["material_tag"]) else -1

        avg_temp = None
        node_temps = [temp_map[n] for n in node_ids if n in temp_map]
        if node_temps:
            avg_temp = float(np.mean(node_temps))
            if temp_unit == "F":
                avg_temp = c_to_f(avg_temp)

        if show_temperature and avg_temp is not None:
            hover_text = f"Solid {solid_id}<br>Material {material_tag}<br>Avg Temp: {avg_temp:.1f} °{temp_unit}"
            fillcolor = "rgba(220, 60, 60, 0.28)"
        elif show_material:
            hover_text = f"Solid {solid_id}<br>Material {material_tag}"
            fillcolor = color_map.get(material_tag, "rgba(120,120,120,0.2)")
        else:
            hover_text = f"Solid {solid_id}"
            fillcolor = "rgba(0,0,0,0)"

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color="#b10000" if show_boundary else "rgba(0,0,0,0)", width=2),
                fill="toself",
                fillcolor=fillcolor,
                hovertemplate=hover_text + "<extra></extra>",
                showlegend=False,
            )
        )

        if show_material:
            label = material_name_map.get(material_tag, str(material_tag))
            fig.add_trace(
                go.Scatter(
                    x=[np.mean([p[0] for p in pts])],
                    y=[np.mean([p[1] for p in pts])],
                    mode="text",
                    text=[label],
                    textfont=dict(size=10, color="#6a0000"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        if show_frontier and solid_id in frontier_map and len(pts) >= 4:
            faces = frontier_map[solid_id]
            solid_edges = [
                (pts[0], pts[1]),
                (pts[1], pts[2]),
                (pts[2], pts[3]),
                (pts[3], pts[0]),
            ]
            for i, face_key in enumerate(["face1", "face2", "face3", "face4"]):
                if face_key in faces and str(faces[face_key]).upper() == "YES":
                    p1, p2 = solid_edges[i]
                    fig.add_trace(
                        go.Scatter(
                            x=[p1[0], p2[0]],
                            y=[p1[1], p2[1]],
                            mode="lines",
                            line=dict(color="#ff6b6b", width=4),
                            hoverinfo="skip",
                            showlegend=False,
                        )
                    )

    if show_node_ids and not coords.empty:
        fig.add_trace(
            go.Scatter(
                x=coords["x"],
                y=coords["y"],
                mode="text",
                text=coords["node_id"].astype(str),
                textfont=dict(size=9, color="#003b8f"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_layout(
        height=560,
        margin=dict(l=5, r=5, t=5, b=5),
        xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def make_material_plot(summary_df: pd.DataFrame, y_col: str, title: str, temp_unit: str) -> go.Figure:
    fig = go.Figure()
    if summary_df.empty:
        fig.update_layout(title=title, height=320)
        return fig

    df = summary_df.copy()
    if temp_unit == "F":
        df[y_col] = c_to_f(df[y_col])

    for material_id in sorted(df["material_id"].dropna().unique().tolist()):
        dfi = df[df["material_id"] == material_id].sort_values("timestep")
        fig.add_trace(
            go.Scatter(
                x=dfi["timestep"],
                y=dfi[y_col],
                mode="lines",
                name=str(dfi["material_section_lookup"].iloc[0]),
            )
        )

    fig.update_layout(
        title=title,
        height=340,
        margin=dict(l=20, r=15, t=50, b=20),
        xaxis_title="Time",
        yaxis_title=f"Temperature (°{temp_unit})",
        legend_title="Material",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def make_node_plot(node_df: pd.DataFrame, fire_df: pd.DataFrame, node_id: Optional[int], temp_unit: str) -> go.Figure:
    fig = go.Figure()
    if node_id is None or node_df.empty:
        fig.update_layout(title="NODE TEMP VS TIME", height=420)
        return fig

    y = node_df["Temperature"].copy()
    if temp_unit == "F":
        y = c_to_f(y)

    fig.add_trace(
        go.Scatter(
            x=node_df["time"],
            y=y,
            mode="lines+markers",
            name=f"Node {node_id}",
        )
    )

    if not fire_df.empty and {"time", "temperature"}.issubset(fire_df.columns):
        fy = fire_df["temperature"].copy()
        if temp_unit == "F":
            fy = c_to_f(fy)
        fig.add_trace(
            go.Scatter(
                x=fire_df["time"],
                y=fy,
                mode="lines",
                name="Fire Curve",
                line=dict(dash="dash"),
            )
        )

    fig.update_layout(
        title="NODE TEMP VS TIME",
        height=440,
        margin=dict(l=20, r=15, t=50, b=20),
        xaxis_title="Time",
        yaxis_title=f"Temperature (°{temp_unit})",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


# ============================================================
# Sidebar
# ============================================================
st.sidebar.header("Database")
folder_text = st.sidebar.text_input("Database folder", value=str(DEFAULT_DB_DIR))
db_dir = Path(folder_text)
db_files = find_db_files(db_dir)

if not db_files:
    st.warning("No .db/.sqlite files found in the selected folder.")
    st.stop()

selected_db_name = st.sidebar.selectbox("Select database file", [p.name for p in db_files])
selected_db_path = str(next(p for p in db_files if p.name == selected_db_name))
summary = get_db_summary(selected_db_path)

if not summary["has_required_tables"]:
    st.error("The selected database is missing one or more required tables: timestamps, node_coordinates, solid_mesh, node_temperatures.")
    st.stop()

with st.sidebar.expander("Database optimization", expanded=False):
    if st.button("Create / refresh views and indexes"):
        execute_script(selected_db_path, INDEX_SQL)
        execute_script(selected_db_path, VW_SOLID_NODES_SQL)
        if "material_list" in set(list_tables(selected_db_path)):
            execute_script(selected_db_path, VW_MATERIAL_TEMP_SQL)
        st.cache_data.clear()
        st.success("Views and indexes refreshed.")

st.sidebar.header("Global options")
temp_unit = st.sidebar.radio("Temperature unit", ["C", "F"], horizontal=True)
active_tab = st.sidebar.radio("Open tab", ["Section Viewer", "Material Summary", "Node History"])


# ============================================================
# Shared light data only
# ============================================================
time_df = get_time_steps(selected_db_path)
if time_df.empty:
    st.error("No timestamps found in the selected database.")
    st.stop()

selected_idx = st.slider("TIME SLIDER", 0, len(time_df) - 1, 0)
selected_timestamp_id = int(time_df.iloc[selected_idx]["id"])
selected_time = float(time_df.iloc[selected_idx]["time"])

metric_cols = st.columns(4)
with metric_cols[0]:
    st.markdown('<div class="panel"><div class="metric-label">DB File</div><div class="metric-value">' + selected_db_name + '</div></div>', unsafe_allow_html=True)
with metric_cols[1]:
    st.markdown('<div class="panel"><div class="metric-label">Selected Time</div><div class="metric-value">' + f'{selected_time:.3f}' + '</div></div>', unsafe_allow_html=True)
with metric_cols[2]:
    st.markdown('<div class="panel"><div class="metric-label">Timestamp ID</div><div class="metric-value">' + str(selected_timestamp_id) + '</div></div>', unsafe_allow_html=True)
with metric_cols[3]:
    st.markdown('<div class="panel"><div class="metric-label">Summary View</div><div class="metric-value">' + ('Ready' if summary['has_summary_view'] else 'Fallback Query') + '</div></div>', unsafe_allow_html=True)


tab_section, tab_material, tab_node = st.tabs(["Section Viewer", "Material Summary", "Node History"])


# ============================================================
# Tab 1: Section Viewer
# ============================================================
with tab_section:
    if active_tab == "Section Viewer":
        geometry = get_section_geometry_payload(selected_db_path)
        section_temp_df = get_section_temperatures(selected_db_path, selected_timestamp_id)

        col1, col2 = st.columns([2.2, 1.0], gap="large")
        with col1:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            show_temperature = st.toggle("Temperature overlay", value=True, key="section_show_temperature")
            show_material = st.toggle("Material labels", value=True, key="section_show_material")
            show_boundary = st.toggle("Solid boundary", value=True, key="section_show_boundary")
            show_node_ids = st.toggle("Node IDs", value=False, key="section_show_node_ids")
            show_frontier = st.toggle("Frontiers", value=True, key="section_show_frontier")

            section_fig = draw_section_view(
                geometry=geometry,
                temp_df=section_temp_df,
                show_temperature=show_temperature,
                show_material=show_material,
                show_boundary=show_boundary,
                show_node_ids=show_node_ids,
                show_frontier=show_frontier,
                temp_unit=temp_unit,
            )
            st.plotly_chart(section_fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown("### Section Info")
            st.write(f"**Current time:** {selected_time:.3f}")
            st.write(f"**Displayed nodes:** {len(section_temp_df)}")
            if temp_unit == "F" and not section_temp_df.empty:
                vals = c_to_f(section_temp_df['Temperature'])
            else:
                vals = section_temp_df['Temperature'] if not section_temp_df.empty else pd.Series(dtype=float)
            if not section_temp_df.empty:
                st.write(f"**Min temp:** {vals.min():.1f} °{temp_unit}")
                st.write(f"**Max temp:** {vals.max():.1f} °{temp_unit}")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Open this tab from the sidebar to run only the section-view queries.")


# ============================================================
# Tab 2: Material Summary
# ============================================================
with tab_material:
    if active_tab == "Material Summary":
        material_summary_df = get_material_summary(selected_db_path)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.plotly_chart(
            make_material_plot(material_summary_df, "avg_temp_material", "AVG TEMP BY MATERIAL", temp_unit),
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.plotly_chart(
            make_material_plot(material_summary_df, "max_temp_material", "MAX TEMP BY MATERIAL", temp_unit),
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        current_slice = material_summary_df[np.isclose(material_summary_df["timestep"], selected_time)].copy()
        if temp_unit == "F" and not current_slice.empty:
            current_slice["avg_temp_material"] = c_to_f(current_slice["avg_temp_material"])
            current_slice["max_temp_material"] = c_to_f(current_slice["max_temp_material"])

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Material Summary at Current Time")
        if current_slice.empty:
            st.info("No material summary rows found for the selected time.")
        else:
            st.dataframe(
                current_slice[["material_id", "material_section_lookup", "avg_temp_material", "max_temp_material"]],
                use_container_width=True,
                hide_index=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Open this tab from the sidebar to run only the material-summary queries.")


# ============================================================
# Tab 3: Node History
# ============================================================
with tab_node:
    if active_tab == "Node History":
        node_coords_df = get_node_coordinates(selected_db_path)
        node_options = sorted(node_coords_df["node_id"].astype(int).unique().tolist()) if not node_coords_df.empty else []
        selected_node = st.selectbox("Pick node", node_options, index=0 if node_options else None)

        node_history_df = get_node_history(selected_db_path, int(selected_node)) if selected_node is not None else pd.DataFrame()
        fire_curve_df = get_fire_curve(selected_db_path)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.plotly_chart(
            make_node_plot(node_history_df, fire_curve_df, int(selected_node) if selected_node is not None else None, temp_unit),
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Node Data Preview")
        if node_history_df.empty:
            st.info("No history found for the selected node.")
        else:
            preview_df = node_history_df.copy()
            if temp_unit == "F":
                preview_df["Temperature"] = c_to_f(preview_df["Temperature"])
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Open this tab from the sidebar to run only the node-history queries.")


with st.expander("Developer Notes", expanded=False):
    st.markdown(
        """
        - This version is intentionally split into 3 tabs so the heavy queries are isolated.
        - Use the sidebar `Open tab` selector to control which query set runs during reruns.
        - Section Viewer only loads geometry and one timestep of node temperatures.
        - Material Summary only loads the material summary view or fallback summary SQL.
        - Node History only loads one node history and the fire curve.
        """
    )
