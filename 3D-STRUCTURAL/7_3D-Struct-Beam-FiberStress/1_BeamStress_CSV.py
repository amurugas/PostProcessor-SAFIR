import sqlite3
import pandas as pd
import re

DB_PATH = "rectslab_5Story.db"  # Replace with your file path
GAUSS_POINT = 1

# Connect and load supporting data
conn = sqlite3.connect(DB_PATH)
timestamps_df = pd.read_sql("SELECT id AS timestamp_id, time AS TimeStep FROM timestamps", conn)
beam_section_df = pd.read_sql("SELECT beam_tag AS beam_id, section AS section_label FROM beam_section", conn)
fiber_table_names = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()

# Load stress values at selected Gauss point
stress_df = pd.read_sql(f"""
    SELECT timestamp_id, beam_id, fiber_index, stress
    FROM beam_fiber_stresses
    WHERE gauss_point = {GAUSS_POINT}
""", conn)

# Merge with time and section metadata
stress_df = stress_df.merge(timestamps_df, on="timestamp_id", how="left")
stress_df = stress_df.merge(beam_section_df, on="beam_id", how="left")

# Prepare final collection
final_rows = []

for section_label in stress_df["section_label"].dropna().unique():
    # Extract just 'w14x22_F' or 'w14x22_U' from full label like 'W14x22_F_S20.TEM'
    match = re.search(r"(w\d+x\d+_[FU])", section_label.lower())
    if match:
        table_name = match.group(1)
    else:
        print(f"❌ Could not extract fiber table from section label: {section_label}")
        continue

    if table_name in fiber_table_names:
        fiber_geom = pd.read_sql(f"SELECT * FROM '{table_name}'", conn)
        subset = stress_df[stress_df["section_label"] == section_label]
        merged = subset.merge(fiber_geom, on="fiber_index", how="left")

        merged = merged[["TimeStep", "beam_id", "section_label", "fiber_index", "x", "y", "stress"]]
        merged.columns = ["TimeStep", "Beam ID", "Beam Section Label", "Fiber ID", "X", "Y", "Stress"]
        final_rows.append(merged)
    else:
        print(f"⚠️ No matching fiber table for {section_label} → tried: {table_name}")

# Combine and export
if final_rows:
    final_df = pd.concat(final_rows, ignore_index=True)
    final_df.to_csv("fiber_stress_output.csv", index=False)
    print("✅ Done! Saved to fiber_stress_output.csv")
else:
    print("❌ No matching section/fiber geometry combinations found.")

conn.close()
