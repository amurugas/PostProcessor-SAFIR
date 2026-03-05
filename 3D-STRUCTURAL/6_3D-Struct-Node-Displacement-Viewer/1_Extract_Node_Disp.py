import sqlite3
import pandas as pd

# === CONFIG ===
DB_PATH = "S2A-3.db"           # Replace with your SQLite database path
OUTPUT_CSV = "S2A-3_Node_Disp.csv"
NODE_IDS = [14, 18, 21, 25, 199, 202, 205, 208, 491, 55]          # Replace with your desired node IDs
METERS_TO_INCHES = 39.3701

# === QUERY AND PROCESS ===
def export_displacement_csv(db_path, node_ids, output_csv):
    with sqlite3.connect(db_path) as conn:
        query = f"""
        SELECT 
            t.time AS TimeStep,
            d.node_id,
            d.D1 * ? AS D1_in,
            d.D2 * ? AS D2_in,
            d.D3 * ? AS D3_in
        FROM node_displacements d
        JOIN timestamps t ON d.timestamp_id = t.id
        WHERE d.node_id IN ({','.join(['?']*len(node_ids))})
        ORDER BY t.time, d.node_id
        """
        df = pd.read_sql_query(query, conn, params=[METERS_TO_INCHES]*3 + node_ids)

    df.to_csv(output_csv, index=False)
    print(f"✅ CSV exported: {output_csv}")

# === RUN ===
export_displacement_csv(DB_PATH, NODE_IDS, OUTPUT_CSV)
