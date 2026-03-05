import os
import sqlite3
import pandas as pd

def process_solid_temperature_db(db_path, base_filename):
    # Connect to the database
    conn = sqlite3.connect(db_path)

    # Create output folder (in the same directory as the db)
    output_folder = os.path.join(os.path.dirname(db_path), "timestepdata")
    os.makedirs(output_folder, exist_ok=True)

    # Load static tables
    timestamps_df = pd.read_sql("SELECT * FROM timestamps", conn)
    solid_mesh_df = pd.read_sql("SELECT * FROM solid_mesh", conn)
    node_coords_df = pd.read_sql("SELECT node_id, x, y FROM node_coordinates", conn)
    material_list_df = pd.read_sql("SELECT * FROM material_list", conn)

    # Process data for each timestamp
    for idx, row in timestamps_df.iterrows():
        timestamp_id = row["id"]

        # Load temperatures for the current timestamp
        temperature_df = pd.read_sql(
            f"SELECT node_id, Temperature FROM node_temperatures WHERE timestamp_id = {timestamp_id}",
            conn
        )

        output_rows = []
        # Iterate over each solid element
        for _, solid in solid_mesh_df.iterrows():
            solid_id = solid["solid_id"]
            # Get node IDs for this element; note that N4 might be missing
            nodes = [solid["N1"], solid["N2"], solid["N3"], solid.get("N4", None)]
            coords = []       # To store x and y for each node
            node_temps = []   # To store temperature for each node

            for nid in nodes:
                # If the node id is missing (e.g. for N4) then record empty values
                if pd.isna(nid):
                    coords.extend(["", ""])
                    node_temps.append("")
                else:
                    # Get node coordinates by matching node_id
                    coord_row = node_coords_df[node_coords_df["node_id"] == nid]
                    if not coord_row.empty:
                        x_val = coord_row.iloc[0]["x"]
                        y_val = coord_row.iloc[0]["y"]
                    else:
                        x_val, y_val = "", ""
                    coords.extend([x_val, y_val])

                    # Get node temperature from the temperature table for current timestamp
                    temp_row = temperature_df[temperature_df["node_id"] == nid]
                    if not temp_row.empty:
                        temp_val = temp_row.iloc[0]["Temperature"]
                    else:
                        temp_val = ""
                    node_temps.append(temp_val)

            # Lookup material name using material_tag from the material_list table
            material_tag = solid["material_tag"]
            mat_row = material_list_df[material_list_df["material_tag"] == material_tag]
            if not mat_row.empty:
                material_name = mat_row.iloc[0]["material_name"]
            else:
                material_name = ""

            # Create a row with the required format:
            # [solid_id, N1_x, N1_y, N2_x, N2_y, N3_x, N3_y, N4_x, N4_y, material_name, N1_temp, N2_temp, N3_temp, N4_temp]
            output_rows.append([solid_id] + coords + [material_name] + node_temps)

        # Define the columns for the output DataFrame
        columns = [
            "solid_id",
            "N1_x", "N1_y",
            "N2_x", "N2_y",
            "N3_x", "N3_y",
            "N4_x", "N4_y",
            "material_name",
            "N1_temperature", "N2_temperature", "N3_temperature", "N4_temperature"
        ]

        # Create DataFrame and save as CSV
        output_df = pd.DataFrame(output_rows, columns=columns)
        csv_filename = f"{base_filename}_{idx + 1}.csv"
        output_df.to_csv(os.path.join(output_folder, csv_filename), index=False)
        print(f"Saved timestamp {timestamp_id} to {csv_filename}")

    conn.close()

if __name__ == "__main__":
    db_path = input("Enter path to your SQLite database (.db): ")
    base_filename = input("Enter base name for output files: ")
    process_solid_temperature_db(db_path, base_filename)
