import os
import sqlite3
import pandas as pd

# --- CONVERSIONS ---
M_TO_FT = 3.28084
PA_TO_KSI = 1 / 6894757.2932

def create_surface_contour_timesteps(db_path, base_filename):
    # Connect to DB
    conn = sqlite3.connect(db_path)
    output_folder = os.path.join(os.path.dirname(db_path), "timestepdata")
    os.makedirs(output_folder, exist_ok=True)

    # Load tables into dataframes
    timestamps_df = pd.read_sql("SELECT id AS timestamp_id, time FROM timestamps", conn)
    shell_nodes_df = pd.read_sql("SELECT shell_id, N1, N2, N3, N4 FROM shell_nodes", conn)
    node_coords_df = pd.read_sql("SELECT node_id, x, y, z FROM node_coordinates", conn)
    displacements_df = pd.read_sql("SELECT node_id, timestamp_id, D1, D2, D3 FROM node_displacements", conn)
    conn.close()

    # "Melt" shell_nodes so each row is (shell_id, node_position, node_id)
    # node_position is one of N1, N2, N3, N4
    shell_nodes_melted = shell_nodes_df.melt(
        id_vars=["shell_id"],
        value_vars=["N1", "N2", "N3", "N4"],
        var_name="node_position",
        value_name="node_id"
    )
    # Drop any rows where node_id is NULL (triangular shells missing N4)
    shell_nodes_melted.dropna(subset=["node_id"], inplace=True)
    shell_nodes_melted["node_id"] = shell_nodes_melted["node_id"].astype(int)

    # Merge everything into one big table
    # We'll have columns:
    #   [shell_id, node_position, node_id, timestamp_id, D1, D2, D3, x, y, z]
    merged_df = (
        shell_nodes_melted
        .merge(displacements_df, on="node_id", how="left")
        .merge(node_coords_df, on="node_id", how="left")
    )

    # We will iterate over each timestamp (row in timestamps_df)
    for idx, ts_row in timestamps_df.iterrows():
        ts_id = ts_row["timestamp_id"]
        ts_time = ts_row["time"]

        # Filter merged data for just this timestamp
        subset = merged_df[merged_df["timestamp_id"] == ts_id].copy()

        if subset.empty:
            # If there's no data for this time step, skip
            continue

        # Pivot so that each shell_id is one row, each node_position (N1..N4) becomes columns
        # We'll pivot x, y, z, D1, D2, D3
        pivot_cols = ["x", "y", "z", "D1", "D2", "D3"]
        pivoted = subset.pivot_table(
            index="shell_id",
            columns="node_position",
            values=pivot_cols,
            aggfunc="first"
        )

        # pivoted has multi-level columns like ( "x", "N1" ), ( "x", "N2" ), ...
        # Flatten them so we get columns named e.g. "N1_x", "N1_z", "N1_D1", etc.
        pivoted.columns = [f"{pos}_{col}" for col, pos in pivoted.columns]
        pivoted.reset_index(inplace=True)

        # Rename pivoted columns to match your old code’s pattern:
        #   N1_x → node1_x, N1_D1 → disp1_x, etc.
        # We'll define a helper map to transform:
        #   Nx -> nodeX
        #   D1 -> dispX, D2 -> dispY, D3 -> dispZ
        col_map = {}
        for c in pivoted.columns:
            if c == "shell_id":
                continue

            # c might look like "N1_x", "N1_D1", "N2_z", etc.
            node_pos, field = c.split("_", maxsplit=1)  # e.g. node_pos="N1", field="x"
            # Convert something like "N1" → "node1"
            node_num = node_pos[1:]  # e.g. "1"
            node_str = f"node{node_num}"

            new_c = ""
            if field == "x":
                new_c = f"{node_str}_x"
            elif field == "y":
                new_c = f"{node_str}_y"
            elif field == "z":
                new_c = f"{node_str}_z"
            elif field == "D1":
                new_c = f"disp{node_num}_x"
            elif field == "D2":
                new_c = f"disp{node_num}_y"
            elif field == "D3":
                new_c = f"disp{node_num}_z"
            else:
                new_c = c  # fallback

            col_map[c] = new_c

        pivoted.rename(columns=col_map, inplace=True)

        # Now pivoted has columns like:
        #   shell_id, node1_x, node1_y, node1_z, disp1_x, disp1_y, disp1_z, node2_x, ...
        # Next, do the z-displacement normalization over disp?_z
        disp_z_cols = [f"disp{i}_z" for i in range(1, 5) if f"disp{i}_z" in pivoted.columns]

        # If there's no z data at all, skip the normalization
        if len(disp_z_cols) > 0:
            z_values = pivoted[disp_z_cols].values.flatten()
            z_min, z_max = z_values.min(), z_values.max()

            # Create new columns contour1..contour4
            for i in range(1, 5):
                col_dz = f"disp{i}_z"
                contour_col = f"contour{i}"
                if col_dz not in pivoted.columns:
                    pivoted[contour_col] = float("nan")
                else:
                    if z_max == z_min:
                        # avoid divide-by-zero if all z are the same
                        pivoted[contour_col] = 0.0
                    else:
                        pivoted[contour_col] = (pivoted[col_dz] - z_min) / (z_max - z_min)
        else:
            # No displacement z columns found
            for i in range(1, 5):
                pivoted[f"contour{i}"] = float("nan")

        # Reindex to match the original column order from your old code
        ordered_columns = [
            "shell_id",
            # node1 + disp1
            "node1_x", "node1_y", "node1_z",
            "disp1_x", "disp1_y", "disp1_z",
            # node2 + disp2
            "node2_x", "node2_y", "node2_z",
            "disp2_x", "disp2_y", "disp2_z",
            # node3 + disp3
            "node3_x", "node3_y", "node3_z",
            "disp3_x", "disp3_y", "disp3_z",
            # node4 + disp4
            "node4_x", "node4_y", "node4_z",
            "disp4_x", "disp4_y", "disp4_z",
            # contours
            "contour1", "contour2", "contour3", "contour4"
        ]
        # If some columns don't exist (e.g. triangular), reindex will fill them with NaN
        pivoted = pivoted.reindex(columns=ordered_columns, fill_value=None)

        # Save CSV with loop index
        csv_filename = f"{base_filename}_{idx+1}.csv"
        csv_path = os.path.join(output_folder, csv_filename)
        pivoted.to_csv(csv_path, index=False)
        print(f"Saved timestamp {idx+1} (DB id={ts_id}, time={ts_time}) to {csv_filename}")

def create_beam_contour_timesteps(db_path, base_filename):
    conn = sqlite3.connect(db_path)
    output_folder = os.path.join(os.path.dirname(db_path), "timestepdata")
    os.makedirs(output_folder, exist_ok=True)

    # 1) Load tables into DataFrames
    timestamps_df = pd.read_sql("SELECT id AS timestamp_id, time FROM timestamps", conn)
    beam_nodes_df = pd.read_sql("SELECT beam_id, N1, N2 FROM beam_nodes", conn)
    node_coords_df = pd.read_sql("SELECT node_id, x, y, z FROM node_coordinates", conn)
    displacements_df = pd.read_sql("SELECT node_id, timestamp_id, D1, D2, D3 FROM node_displacements", conn)
    conn.close()

    displacements_df[["D1", "D2", "D3"]] *= M_TO_FT


    # 2) Melt beam_nodes so each row is (beam_id, node_position, node_id), for N1 and N2
    beam_nodes_melted = beam_nodes_df.melt(
        id_vars=["beam_id"],
        value_vars=["N1", "N2"],     # Only these two
        var_name="node_position",
        value_name="node_id"
    )
    # If any node_id is NaN, drop it (shouldn't happen with N1, N2, but just to be safe)
    beam_nodes_melted.dropna(subset=["node_id"], inplace=True)
    beam_nodes_melted["node_id"] = beam_nodes_melted["node_id"].astype(int)

    merged_df = (
        beam_nodes_melted
        .merge(displacements_df, on="node_id", how="left")
        .merge(node_coords_df, on="node_id", how="left")
    )

    for idx, ts_row in timestamps_df.iterrows():
        ts_id = ts_row["timestamp_id"]
        ts_time = ts_row["time"]

        # Filter to just this timestamp
        subset = merged_df[merged_df["timestamp_id"] == ts_id].copy()
        if subset.empty:
            continue

        # Pivot so each beam_id is one row, and node_position = {N1,N2} becomes columns
        pivot_cols = ["x", "y", "z", "D1", "D2", "D3"]
        pivoted = subset.pivot_table(
            index="beam_id",        # each beam in one row
            columns="node_position",
            values=pivot_cols,
            aggfunc="first"
        )
        # Flatten multi-index columns from (x, N1) → "N1_x"
        pivoted.columns = [f"{pos}_{col}" for col, pos in pivoted.columns]
        pivoted.reset_index(inplace=True)

        # 5) Rename columns from N1_x → node1_x, etc.
        #    Also rename D1->disp?_x, D2->disp?_y, D3->disp?_z for each node
        col_map = {}
        for c in pivoted.columns:
            if c == "beam_id":
                continue
            # c might look like "N1_x", "N2_D3"
            node_pos, field = c.split("_", maxsplit=1)  # e.g. node_pos="N1", field="x"
            node_num = node_pos[1:]  # "1" or "2"
            node_str = f"node{node_num}"

            # Our new naming pattern
            if field == "x":
                new_c = f"{node_str}_x"
            elif field == "y":
                new_c = f"{node_str}_y"
            elif field == "z":
                new_c = f"{node_str}_z"
            elif field == "D1":
                new_c = f"disp{node_num}_x"
            elif field == "D2":
                new_c = f"disp{node_num}_y"
            elif field == "D3":
                new_c = f"disp{node_num}_z"
            else:
                new_c = c

            col_map[c] = new_c

        pivoted.rename(columns=col_map, inplace=True)

        # 6) Create normalized contours for disp?_z
        #    We'll have exactly two possible columns: disp1_z, disp2_z
        disp_z_cols = []
        for i in range(1, 3):  # beam has 2 nodes
            col_name = f"disp{i}_z"
            if col_name in pivoted.columns:
                disp_z_cols.append(col_name)

        if disp_z_cols:
            z_values = pivoted[disp_z_cols].values.flatten()
            z_min, z_max = z_values.min(), z_values.max()
            # Create contour1, contour2
            for i in range(1, 3):
                col_z = f"disp{i}_z"
                contour_col = f"contour{i}"
                if col_z not in pivoted.columns:
                    pivoted[contour_col] = float("nan")
                else:
                    if z_max == z_min:
                        pivoted[contour_col] = 0.0
                    else:
                        pivoted[contour_col] = (pivoted[col_z] - z_min) / (z_max - z_min)
        else:
            # No z data found
            pivoted["contour1"] = float("nan")
            pivoted["contour2"] = float("nan")

        # 7) Reindex columns in your desired final order
        ordered_columns = [
            "beam_id",
            "node1_x", "node1_y", "node1_z",
            "disp1_x", "disp1_y", "disp1_z",
            "node2_x", "node2_y", "node2_z",
            "disp2_x", "disp2_y", "disp2_z",
            "contour1", "contour2"
        ]
        pivoted = pivoted.reindex(columns=ordered_columns, fill_value=None)

        # 8) Save CSV by loop index
        csv_filename = f"{base_filename}_{idx+1}.csv"
        csv_path = os.path.join(output_folder, csv_filename)
        pivoted.to_csv(csv_path, index=False)
        print(f"Saved beam data for timestamp {idx+1} (DB id={ts_id}, time={ts_time}) to {csv_filename}")

def create_beam_strain_stress_contour_timesteps(db_path, base_filename):
    conn = sqlite3.connect(db_path)
    output_folder = os.path.join(os.path.dirname(db_path), "timestepdata")
    os.makedirs(output_folder, exist_ok=True)

    # Load core tables
    timestamps_df = pd.read_sql("SELECT id AS timestamp_id, time FROM timestamps", conn)
    beam_nodes_df = pd.read_sql("SELECT beam_id, N1, N2 FROM beam_nodes", conn)
    node_coords_df = pd.read_sql("SELECT node_id, x, y, z FROM node_coordinates", conn)
    displacements_df = pd.read_sql("SELECT node_id, timestamp_id, D1, D2, D3 FROM node_displacements", conn)
    strain_df = pd.read_sql("SELECT * FROM beam_fiber_strains", conn)
    stress_df = pd.read_sql("SELECT * FROM beam_fiber_stresses", conn)
    conn.close()
    displacements_df[["D1", "D2", "D3"]] *= M_TO_FT
    stress_df["stress"] *= PA_TO_KSI

    # Melt beam nodes to long form
    beam_nodes_melted = beam_nodes_df.melt(
        id_vars=["beam_id"],
        value_vars=["N1", "N2"],
        var_name="node_position",
        value_name="node_id"
    )
    beam_nodes_melted.dropna(subset=["node_id"], inplace=True)
    beam_nodes_melted["node_id"] = beam_nodes_melted["node_id"].astype(int)

    merged_df = (
        beam_nodes_melted
        .merge(displacements_df, on="node_id", how="left")
        .merge(node_coords_df, on="node_id", how="left")
    )

    for idx, ts_row in timestamps_df.iterrows():
        ts_id = ts_row["timestamp_id"]
        ts_time = ts_row["time"]
        subset = merged_df[merged_df["timestamp_id"] == ts_id].copy()
        if subset.empty:
            continue

        # Pivot to wide form
        pivot_cols = ["x", "y", "z", "D1", "D2", "D3"]
        pivoted = subset.pivot_table(
            index="beam_id",
            columns="node_position",
            values=pivot_cols,
            aggfunc="first"
        )
        pivoted.columns = [f"{pos}_{col}" for col, pos in pivoted.columns]
        pivoted.reset_index(inplace=True)

        col_map = {}
        for c in pivoted.columns:
            if c == "beam_id":
                continue
            node_pos, field = c.split("_", maxsplit=1)
            node_num = node_pos[1:]
            node_str = f"node{node_num}"
            if field == "x":
                new_c = f"{node_str}_x"
            elif field == "y":
                new_c = f"{node_str}_y"
            elif field == "z":
                new_c = f"{node_str}_z"
            elif field == "D1":
                new_c = f"disp{node_num}_x"
            elif field == "D2":
                new_c = f"disp{node_num}_y"
            elif field == "D3":
                new_c = f"disp{node_num}_z"
            else:
                new_c = c
            col_map[c] = new_c

        pivoted.rename(columns=col_map, inplace=True)

        # Compute strain/stress summaries
        ts_strain = strain_df[strain_df["timestamp_id"] == ts_id]
        ts_stress = stress_df[stress_df["timestamp_id"] == ts_id]

        strain_summary = (
            ts_strain.groupby("beam_id")["strain"]
            .agg(min_strain="min", max_strain="max")
            .reset_index()
        )
        stress_summary = (
            ts_stress.groupby("beam_id")["stress"]
            .agg(min_stress="min", max_stress="max")
            .reset_index()
        )

        summary_df = pd.merge(strain_summary, stress_summary, on="beam_id", how="outer")
        pivoted = pd.merge(pivoted, summary_df, on="beam_id", how="left")

        # Contour columns normalized based on max_strain
        if "max_strain" in pivoted and "min_strain" in pivoted:
            s_min = pivoted["min_strain"].min()
            s_max = pivoted["max_strain"].max()
            if s_max != s_min:
                pivoted["contour1"] = (pivoted["max_strain"] - s_min) / (s_max - s_min)
                pivoted["contour2"] = (pivoted["min_strain"] - s_min) / (s_max - s_min)
            else:
                pivoted["contour1"] = 0.0
                pivoted["contour2"] = 0.0
        else:
            pivoted["contour1"] = float("nan")
            pivoted["contour2"] = float("nan")

        # Output columns
        ordered_columns = [
            "beam_id",
            "node1_x", "node1_y", "node1_z",
            "disp1_x", "disp1_y", "disp1_z",
            "node2_x", "node2_y", "node2_z",
            "disp2_x", "disp2_y", "disp2_z",
            "contour1", "contour2", "max_strain", "min_strain", "max_stress", "min_stress"
        ]
        pivoted = pivoted.reindex(columns=ordered_columns, fill_value=None)

        csv_filename = f"{base_filename}_strainstress_{idx+1}.csv"
        csv_path = os.path.join(output_folder, csv_filename)
        pivoted.to_csv(csv_path, index=False)
        print(f"Saved contour + strain/stress summary for timestamp {idx+1} to {csv_filename}")

    return output_folder

# Example usage (user can run this with appropriate db_path)
# create_beam_strain_stress_contour_timesteps("rectslab_5Story.db", "beamstrain")

# def create_beam_strain_stress_summary_timesteps(db_path, base_filename):
#     conn = sqlite3.connect(db_path)
#     output_folder = os.path.join(os.path.dirname(db_path), "timestepdata")
#     os.makedirs(output_folder, exist_ok=True)
#
#     # Get all timestamps
#     timestamps_df = pd.read_sql("SELECT id AS timestamp_id, time FROM timestamps", conn)
#
#     # Load beam strain and stress tables
#     strain_df = pd.read_sql("SELECT * FROM beam_fiber_strains", conn)
#     stress_df = pd.read_sql("SELECT * FROM beam_fiber_stresses", conn)
#     conn.close()
#
#     for idx, ts_row in timestamps_df.iterrows():
#         ts_id = ts_row["timestamp_id"]
#         ts_time = ts_row["time"]
#
#         # Filter data for current timestep
#         ts_strain = strain_df[strain_df["timestamp_id"] == ts_id]
#         ts_stress = stress_df[stress_df["timestamp_id"] == ts_id]
#
#         # Aggregate min/max per beam_id and gauss_point
#         strain_summary = (
#             ts_strain.groupby(["beam_id", "gauss_point"])["strain"]
#             .agg(min_strain="min", max_strain="max")
#             .reset_index()
#         )
#
#         stress_summary = (
#             ts_stress.groupby(["beam_id", "gauss_point"])["stress"]
#             .agg(min_stress="min", max_stress="max")
#             .reset_index()
#         )
#
#         # Merge summaries
#         summary = pd.merge(strain_summary, stress_summary, on=["beam_id", "gauss_point"], how="outer")
#         summary.insert(0, "timestamp_id", ts_id)
#         summary.insert(1, "time", ts_time)
#
#         # Save to CSV
#         csv_filename = f"{base_filename}_strainstress_{idx+1}.csv"
#         csv_path = os.path.join(output_folder, csv_filename)
#         summary.to_csv(csv_path, index=False)
#         print(f"Saved strain/stress summary for timestamp {idx+1} (time={ts_time}) to {csv_filename}")
#
#     return output_folder


if __name__ == "__main__":
    # db_path = input("Enter path to your SQLite database (.db): ").strip()
    # base_filename = input("Enter base name for surface files: ").strip()
    # base2_filename = input("Enter base name for beam files: ").strip()
    db_path = "C:/Users/am1/PycharmProjects/PostProcessor-SAFIR/S2A.db"
    base_filename = "2_Surface/Step"
    base2_filename = "1_Beam/BeamStep"
    create_surface_contour_timesteps(db_path, base_filename)
    create_beam_contour_timesteps(db_path, base2_filename)
    #create_beam_strain_stress_contour_timesteps("S2A.db", "5_StressStrain/2summary")