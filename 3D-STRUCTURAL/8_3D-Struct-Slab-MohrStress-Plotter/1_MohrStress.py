import logging
import math
import sqlite3
import numpy as np
import pandas as pd

# ------------------------------
# Configure logging
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

TBL_STRESS = "shell_strains"
TBL_ELEMS  = "shell_nodes"
TBL_NODES  = "node_coordinates"

# ------------------------------
# Helpers (same as before)
# ------------------------------
def _poly_area_xy(pts):
    if len(pts) < 3:
        return 0.0
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    return abs(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))

def mohr_principal_2d(sx, sy, txy):
    s_avg = 0.5 * (sx + sy)
    R = math.hypot(0.5 * (sx - sy), txy)
    sigma1 = s_avg + R
    sigma2 = s_avg - R
    tau_max = R
    theta = 0.5 * math.atan2(2.0 * txy, (sx - sy + 1e-30))
    return sigma1, sigma2, tau_max, theta

# ------------------------------
# Compute for one timestep
# ------------------------------
def _compute_nodal_principal_for_step(con, timestamp_id, average_method):
    """
    Compute nodal principal stresses for a single timestep.
    Returns DataFrame: node_id,x,y,z,sigma1,sigma2,tau_max,theta_rad
    """
    logger.debug(f"Computing nodal principal stresses for timestamp_id={timestamp_id}, method={average_method}")

    # element mean stresses (avg over integration points / thickness)
    elt = pd.read_sql_query(
        f"""
        SELECT shell_id, AVG(Sx) AS Sx, AVG(Sy) AS Sy, AVG(Sz) AS Sxy
        FROM {TBL_STRESS}
        WHERE timestamp_id = ?
        GROUP BY shell_id
        """, con, params=[timestamp_id]
    )
    if elt.empty:
        return pd.DataFrame(columns=["node_id","x","y","z","sigma1","sigma2","tau_max","theta_rad"])

    elems = pd.read_sql_query(
        f"""
        SELECT sn.shell_id, sn.N1, sn.N2, sn.N3, sn.N4
        FROM {TBL_ELEMS} sn
        INNER JOIN (SELECT DISTINCT shell_id FROM {TBL_STRESS} WHERE timestamp_id = ?) e
          ON sn.shell_id = e.shell_id
        """, con, params=[timestamp_id]
    ).merge(elt, on="shell_id", how="inner")

    def row_nodes(r):
        vals = [r["N1"], r["N2"], r["N3"], r.get("N4", None)]
        return [int(v) for v in vals if v not in (None, 0)]
    elems["nodes"] = elems.apply(row_nodes, axis=1)

    node_ids = sorted({n for nl in elems["nodes"] for n in nl})
    if not node_ids:
        return pd.DataFrame(columns=["node_id","x","y","z","sigma1","sigma2","tau_max","theta_rad"])

    nodes = pd.read_sql_query(
        f"SELECT node_id, x, y, z FROM {TBL_NODES} WHERE node_id IN ({','.join(['?']*len(node_ids))})",
        con, params=node_ids
    )
    node_xy  = {int(r.node_id): (float(r.x), float(r.y)) for _, r in nodes.iterrows()}
    node_xyz = {int(r.node_id): (float(r.x), float(r.y), float(r.z)) for _, r in nodes.iterrows()}

    # element XY areas (weights)
    areas = []
    for _, r in elems.iterrows():
        pts = [node_xy[n] for n in r["nodes"] if n in node_xy]
        areas.append(_poly_area_xy(pts))
    elems["A"] = areas

    if average_method == "principal":
        # compute principal per element then average to nodes
        s1_sum, s2_sum, tmax_sum, c2_sum, s2ang_sum, wsum = {}, {}, {}, {}, {}, {}
        for _, r in elems.iterrows():
            s1, s2, tmax, th = mohr_principal_2d(r.Sx, r.Sy, r.Sxy)
            nl = r["nodes"]
            if not nl: continue
            w = (r["A"] or 0.0) / len(nl)
            c2, s2a = math.cos(2.0 * th), math.sin(2.0 * th)
            for nid in nl:
                s1_sum[nid]    = s1_sum.get(nid, 0.0)    + w * s1
                s2_sum[nid]    = s2_sum.get(nid, 0.0)    + w * s2
                tmax_sum[nid]  = tmax_sum.get(nid, 0.0)  + w * tmax
                c2_sum[nid]    = c2_sum.get(nid, 0.0)    + w * c2
                s2ang_sum[nid] = s2ang_sum.get(nid, 0.0) + w * s2a
                wsum[nid]      = wsum.get(nid, 0.0)      + w
        rows = []
        for nid, w in wsum.items():
            if w <= 0: continue
            s1 = s1_sum[nid] / w
            s2 = s2_sum[nid] / w
            tmax = tmax_sum[nid] / w
            theta = 0.5 * math.atan2(s2ang_sum[nid] / w, c2_sum[nid] / w)
            x, y, z = node_xyz.get(nid, (0.0, 0.0, 0.0))
            rows.append((nid, x, y, z, s1, s2, tmax, theta))
        df = pd.DataFrame(rows, columns=["node_id","x","y","z","sigma1","sigma2","tau_max","theta_rad"])

    else:  # tensor
        acc, wsum = {}, {}
        for _, r in elems.iterrows():
            nl = r["nodes"]
            if not nl: continue
            w = (r["A"] or 0.0) / len(nl)
            for nid in nl:
                acc.setdefault(nid, np.zeros(3))
                wsum[nid] = wsum.get(nid, 0.0) + w
                acc[nid] += w * np.array([r.Sx, r.Sy, r.Sxy])
        rows = []
        for nid, v in acc.items():
            w = wsum.get(nid, 0.0)
            if w <= 0: continue
            sx, sy, sxy = (v / w).tolist()
            s1, s2, tmax, th = mohr_principal_2d(sx, sy, sxy)
            x, y, z = node_xyz.get(nid, (0.0, 0.0, 0.0))
            rows.append((nid, x, y, z, s1, s2, tmax, th))
        df = pd.DataFrame(rows, columns=["node_id","x","y","z","sigma1","sigma2","tau_max","theta_rad"])

    return df
# ------------------------------
# Store results for all timesteps
# ------------------------------
def store_nodal_principal_stresses(db_path, average_method="tensor", overwrite=False):
    """
    Computes nodal principal stresses for all timesteps and writes to nodal_principal_stress.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    logger.info(f"Ensuring output table exists in {db_path}")
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS nodal_principal_stress (
      timestamp_id INTEGER NOT NULL,
      node_id      INTEGER NOT NULL,
      sigma1       REAL    NOT NULL,
      sigma2       REAL    NOT NULL,
      tau_max      REAL    NOT NULL,
      theta_rad    REAL    NOT NULL,
      x            REAL    NOT NULL,
      y            REAL    NOT NULL,
      z            REAL    NOT NULL,
      method       TEXT    NOT NULL,
      PRIMARY KEY (timestamp_id, node_id, method)
    );
    CREATE INDEX IF NOT EXISTS idx_nps_time_method ON nodal_principal_stress (timestamp_id, method);
    """)
    con.commit()

    steps = [r[0] for r in cur.execute(
        f"SELECT DISTINCT timestamp_id FROM {TBL_STRESS} ORDER BY timestamp_id"
    ).fetchall()]

    logger.info(f"Found {len(steps)} timesteps to process.")

    if overwrite:
        logger.warning(f"Deleting existing rows for method={average_method}")
        cur.execute("DELETE FROM nodal_principal_stress WHERE method=?", (average_method,))
        con.commit()

    insert_sql = """
    INSERT INTO nodal_principal_stress
      (timestamp_id, node_id, sigma1, sigma2, tau_max, theta_rad, x, y, z, method)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(timestamp_id, node_id, method) DO UPDATE SET
      sigma1=excluded.sigma1,
      sigma2=excluded.sigma2,
      tau_max=excluded.tau_max,
      theta_rad=excluded.theta_rad,
      x=excluded.x, y=excluded.y, z=excluded.z
    """

    for i, ts in enumerate(steps, 1):
        logger.info(f"[{i}/{len(steps)}] Processing timestep_id={ts}")
        df = _compute_nodal_principal_for_step(con, ts, average_method)
        if df.empty:
            logger.warning(f"No nodal stresses found for timestep_id={ts}, skipping")
            continue

        rows = [
            (int(ts), int(r.node_id), float(r.sigma1), float(r.sigma2),
             float(r.tau_max), float(r.theta_rad), float(r.x), float(r.y), float(r.z),
             average_method)
            for _, r in df.iterrows()
        ]
        cur.executemany(insert_sql, rows)
        con.commit()
        logger.debug(f"Inserted {len(rows)} rows for timestep_id={ts}")

    logger.info("Finished storing nodal principal stresses.")
    con.close()


if __name__ == "__main__":
    store_nodal_principal_stresses("S2A-9_Bays.db", average_method="tensor", overwrite=True)
