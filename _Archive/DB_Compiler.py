import os
import sqlite3
import logging
import pandas as pd
from lxml import objectify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.create_tables()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.executescript("""        
            
            CREATE TABLE IF NOT EXISTS Time_temperature_curve (
                id INTEGER PRIMARY KEY,
                time REAL,
                temperature REAL
            );
                      
           CREATE TABLE IF NOT EXISTS model_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                description TEXT
            );
            
            CREATE TABLE IF NOT EXISTS timestamps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time REAL NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS node_coordinates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER NOT NULL,
                x REAL,
                y REAL,
                z REAL
            );
            
             CREATE TABLE IF NOT EXISTS beam_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                beam_id INTEGER NOT NULL,
                N1 REAL, N3 REAL, N2 REAL, N4 REAL,
                beam_tag REAL
            );
            
            CREATE TABLE IF NOT EXISTS shell_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shell_id INTEGER NOT NULL,
                N1 REAL, N2 REAL, N3 REAL, N4 REAL,
                shell_tag REAL
            );
            
            CREATE TABLE IF NOT EXISTS node_fixity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER NOT NULL,
                DOF1 TEXT DEFAULT 'NO',
                DOF2 TEXT DEFAULT 'NO',
                DOF3 TEXT DEFAULT 'NO',
                DOF4 TEXT DEFAULT 'NO',
                DOF5 TEXT DEFAULT 'NO',
                DOF6 TEXT DEFAULT 'NO',
                DOF7 TEXT DEFAULT 'NO'
            );
            
            CREATE TABLE IF NOT EXISTS beam_section (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                beam_tag INTEGER NOT NULL,
                section TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS shell_section (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shell_tag INTEGER NOT NULL,
                section TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS shell_loads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                load_id INTEGER NOT NULL,
                load_fct TEXT,
                shell_id INTEGER NOT NULL,
                P1 REAL,
                P2 REAL,
                P3 REAL
            );
            
            CREATE TABLE IF NOT EXISTS material_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_tag INTEGER NOT NULL,
                material_name TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS node_displacements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                D1 REAL DEFAULT 0,
                D2 REAL DEFAULT 0,
                D3 REAL DEFAULT 0,
                D4 REAL DEFAULT 0,
                D5 REAL DEFAULT 0,
                D6 REAL DEFAULT 0,
                D7 REAL DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS beam_forces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_id INTEGER NOT NULL,
                beam_id INTEGER NOT NULL,
                gauss_point INTEGER NOT NULL,
                N REAL,
                Mz REAL,
                My REAL,
                Mw REAL,
                Mr2 REAL,
                Vz REAL,
                Vy REAL
            );

            CREATE TABLE IF NOT EXISTS shell_strains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_id INTEGER NOT NULL,
                shell_id INTEGER NOT NULL,
                integration_point INTEGER,
                thickness INTEGER,
                Sx REAL, Sy REAL, Sz REAL,
                Px REAL, Py REAL, Pz REAL,
                Dx REAL, Dy REAL, Dz REAL
            );

            CREATE TABLE IF NOT EXISTS rebar_strains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_id INTEGER NOT NULL,
                shell_id INTEGER NOT NULL,
                nga INTEGER NOT NULL,
                rebar_id INTEGER NOT NULL,
                eps_sx REAL,
                eps_sy REAL
            );
            
            """)
            logging.info("Database tables ensured.")

    def create_views(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
            DROP VIEW IF EXISTS beam_section_lookup;
            CREATE VIEW beam_section_lookup AS
            SELECT 
                bn.beam_id AS beam_id,
                bs.section AS section
            FROM 
                beam_nodes bn
            JOIN 
                beam_section bs ON bn.beam_tag = bs.beam_tag;
                
            DROP VIEW IF EXISTS shell_section_lookup;
            CREATE VIEW shell_section_lookup AS
            SELECT 
                sn.shell_id AS shell_id,
                ss.section AS section
            FROM 
                shell_nodes sn
            JOIN 
                shell_section ss ON sn.shell_tag = ss.shell_tag;    
                
            """)
            logging.info("Views created.")

    def clear_database(self):
        confirm = input("Are you sure you want to clear the database? (yes/no): ")
        if confirm.lower() != 'yes':
            logging.info("Database clearing aborted.")
            return
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.executescript("""            
            DELETE FROM timestamps;
            DELETE FROM node_coordinates;
            DELETE FROM beam_nodes;
            DELETE FROM shell_nodes;
            DELETE FROM node_fixity;
            DELETE FROM beam_section;
            DELETE FROM shell_section;
            DELETE FROM beam_forces;
            DELETE FROM shell_strains;
            DELETE FROM rebar_strains;
            DELETE FROM node_displacements;
            DELETE FROM beam_forces;
            DELETE FROM model_data;
            DELETE FROM shell_loads;
            DELETE FROM material_list;
                    
            DELETE FROM sqlite_sequence WHERE name='timestamps';
            DELETE FROM sqlite_sequence WHERE name='node_coordinates';
            DELETE FROM sqlite_sequence WHERE name='beam_nodes';
            DELETE FROM sqlite_sequence WHERE name='shell_nodes';
            DELETE FROM sqlite_sequence WHERE name='node_fixity';
            DELETE FROM sqlite_sequence WHERE name='beam_section';
            DELETE FROM sqlite_sequence WHERE name='shell_section';
            DELETE FROM sqlite_sequence WHERE name='beam_forces';
            DELETE FROM sqlite_sequence WHERE name='shell_strains';
            DELETE FROM sqlite_sequence WHERE name='rebar_strains';
            DELETE FROM sqlite_sequence WHERE name='node_displacements';
            DELETE FROM sqlite_sequence WHERE name='beam_forces';
            DELETE FROM sqlite_sequence WHERE name='model_data';
            DELETE FROM sqlite_sequence WHERE name='shell_loads';
            DELETE FROM sqlite_sequence WHERE name='material_list';
            """)
            logging.info("Database cleared.")


class FileParser:
    def __init__(self, db_manager):
        self.db = db_manager

    def parse_xml_data(self, xml_file_path):
        with open(xml_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f"<ROOT>{f.read()}</ROOT>"
        root = objectify.fromstring(content)

        self.store_model_data(root)
        self.store_node_coordinates(root)
        self.store_beam_nodes(root)
        self.store_shell_nodes(root)

        self.store_node_fixity(root)
        self.store_beam_sections(root)
        self.store_shell_sections(root)
        self.store_shell_loads(root)
        self.store_material_list(root)

        self.store_node_displacements(root)
        self.store_beam_forces(root)
        self.store_shell_strains(root)
        self.store_rebar_strains(root)
    def store_model_data(self, root):
        # SAFIR tag -> description mapping
        metadata_map = {
            "NNODE": "Number of Nodes",
            "NDIM": "Number of Dimensions",
            "NDOFMAX": "Number of Degrees of Freedom",
            "TYPE": "Analysis Type",
            "NM": "Number of Material Types",
            "NBM": "Number of Beam Elements",
            "NBMS": "Number of Beam Section Types",
            "NGBM": "Number of Gaussian Points In Beams",
            "NFBM": "Number of Beam Elements",  # duplicate meaning with NBM?
            "NSH": "Number of Shell Elements",
            "NSHS": "Number of Shell Element Types",
            "NSHELL": "Number of Shell Elements",
            "NGEOSHELL": "Number of Types of Shell Elements",
            "NREBARS": "Num of Rebar Layers",
            "NGSHELLTHICK": "Number of Integration Points In Thickness"
        }

        model_data = []

        for tag, description in metadata_map.items():
            try:
                val = getattr(root.SAFIR_RESULTS, tag)
                model_data.append((tag, str(val), description))
            except AttributeError:
                logging.warning(f"Tag <{tag}> not found in SAFIR_RESULTS.")
                continue

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO model_data (name, value, description)
                VALUES (?, ?, ?)""", model_data)

        logging.info(f"Inserted {len(model_data)} model metadata entries.")

    def store_node_coordinates(self, root):
        nodes = root.SAFIR_RESULTS.NODES.N
        node_data = []

        for node_id, node in enumerate(nodes):
            try:
                x = float(node.P1)
                y = float(node.P2)
                z = float(node.P3)
                node_data.append((node_id + 1, x, y, z))
            except Exception as e:
                logging.warning(f"Error parsing node {node_id + 1}: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO node_coordinates (node_id, x, y, z)
                VALUES (?, ?, ?, ?)
            """, node_data)
        logging.info(f"Inserted {len(node_data)} node coordinates.")

    def store_beam_nodes(self, root):
        beam_nodes = root.SAFIR_RESULTS.BEAMS.BMformat.BM
        beam_node_data = []

        for beam_id, beam in enumerate(beam_nodes):
            try:
                N1 = float(beam.N1)
                N3 = float(beam.N3)
                N2 = float(beam.N2)
                N4 = float(beam.N4)
                beam_tag = float(beam.BMST)
                beam_node_data.append((beam_id + 1, N1, N3, N2, N4, beam_tag))
            except Exception as e:
                logging.warning(f"Error parsing beam {beam_id + 1}: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                        INSERT INTO beam_nodes (beam_id, N1, N3, N2, N4, beam_tag)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, beam_node_data)
        logging.info(f"Inserted {len(beam_node_data)} beam end nodes.")

    def store_shell_nodes(self, root):
        shell_nodes = root.SAFIR_RESULTS.SHELLS.SH
        shell_node_data = []

        for shell_id, shell in enumerate(shell_nodes):
            try:
                N1 = float(shell.N1)
                N2 = float(shell.N2)
                N3 = float(shell.N3)
                N4 = float(shell.N4)
                shell_tag = float(shell.SHST)
                shell_node_data.append((shell_id + 1, N1, N2, N3, N4, shell_tag))
            except Exception as e:
                logging.warning(f"Error parsing shell {shell_id + 1}: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                        INSERT INTO shell_nodes (shell_id, N1, N2, N3, N4, shell_tag)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, shell_node_data)
        logging.info(f"Inserted {len(shell_node_data)} shell end nodes.")

    def store_node_fixity(self, root):
        if not hasattr(root.SAFIR_RESULTS, "FIX"):
            logging.warning("No FIX data found.")
            return

        fixity_data = []
        for node in root.SAFIR_RESULTS.FIX.N:
            node_id = int(node.NN)
            dof_values = ['NO'] * 7  # default for DOF1 to DOF7

            # Iterate through pairs of NDL and CDDL
            ndl_tags = node.findall("NDL")
            cddl_tags = node.findall("CDDL")

            for ndl, cddl in zip(ndl_tags, cddl_tags):
                dof_index = int(ndl) - 1  # zero-based index
                if 0 <= dof_index < 7:
                    dof_values[dof_index] = str(cddl).strip()

            fixity_data.append((node_id, *dof_values))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO node_fixity
                (node_id, DOF1, DOF2, DOF3, DOF4, DOF5, DOF6, DOF7)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", fixity_data)
        logging.info(f"Inserted {len(fixity_data)} node fixity records.")

    def store_beam_sections(self, root):
        if not hasattr(root.SAFIR_RESULTS, "BEAMS") or not hasattr(root.SAFIR_RESULTS.BEAMS, "BMS"):
            logging.warning("No beam sections found in <BEAMS><BMS>.")
            return

        sections = root.SAFIR_RESULTS.BEAMS.BMS.NAME
        beam_section_data = []

        for beam_tag, name in enumerate(sections, start=1):
            section_name = str(name).strip()
            beam_section_data.append((beam_tag, section_name))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                 INSERT INTO beam_section (beam_tag, section)
                 VALUES (?, ?)""", beam_section_data)
        logging.info(f"Inserted {len(beam_section_data)} beam section entries.")

    def store_shell_sections(self, root):
        if not hasattr(root.SAFIR_RESULTS, "SHELLS") or not hasattr(root.SAFIR_RESULTS.SHELLS, "SHS"):
            logging.warning("No shell sections found in <SHELLS><SHS>.")
            return

        sections = root.SAFIR_RESULTS.SHELLS.SHS.NAME
        shell_section_data = []

        for shell_tag, name in enumerate(sections, start=1):
            section_name = str(name).strip()
            shell_section_data.append((shell_tag, section_name))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO shell_section (shell_tag, section)
                VALUES (?, ?)""", shell_section_data)
        logging.info(f"Inserted {len(shell_section_data)} shell section entries.")

    def store_shell_loads(self, root):
        if not hasattr(root.SAFIR_RESULTS, "LOADS"):
            logging.warning("No <LOADS> section found.")
            return

        load_section = root.SAFIR_RESULTS.LOADS
        try:
            load_id = int(load_section.NLOAD)
            load_fct = str(load_section.FCT).strip()
        except Exception as e:
            logging.error(f"Error reading NLOAD/FCT: {e}")
            return

        shell_load_data = []

        for dsh in load_section.DSH:
            try:
                shell_id = int(dsh.SH)
                l_values = dsh.findall("L")
                P1 = float(l_values[0]) if len(l_values) > 0 else 0.0
                P2 = float(l_values[1]) if len(l_values) > 1 else 0.0
                P3 = float(l_values[2]) if len(l_values) > 2 else 0.0

                shell_load_data.append((load_id, load_fct, shell_id, P1, P2, P3))
            except Exception as e:
                logging.warning(f"Error parsing DSH load block: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO shell_loads
                (load_id, load_fct, shell_id, P1, P2, P3)
                VALUES (?, ?, ?, ?, ?, ?)""", shell_load_data)

        logging.info(f"Inserted {len(shell_load_data)} shell load entries.")

    def store_material_list(self, root):
        if not hasattr(root.SAFIR_RESULTS, "MATERIALS"):
            logging.warning("No <MATERIALS> section found.")
            return

        material_tags = root.SAFIR_RESULTS.MATERIALS.findall("MT")
        material_data = []

        for index, mt in enumerate(material_tags, start=1):
            material_name = str(mt).strip()
            material_data.append((index, material_name))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO material_list (material_tag, material_name)
                VALUES (?, ?)""", material_data)

        logging.info(f"Inserted {len(material_data)} materials into material_list.")

    def get_ordered_node_ids(self):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT node_id FROM node_coordinates ORDER BY id ASC")
            return [row[0] for row in cur.fetchall()]

    def store_node_displacements(self, root):
        displacement_data = []
        ordered_node_ids = self.get_ordered_node_ids()

        for step in root.SAFIR_RESULTS.STEP:
            if not hasattr(step, "DISPLACEMENTS"):
                continue

            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            nd_tags = step.DISPLACEMENTS.findall("ND")
            dformat_tags = step.DISPLACEMENTS.findall("Dformat")
            dformat_index = 0

            for index, nd_elem in enumerate(nd_tags):
                if index >= len(ordered_node_ids):
                    logging.warning("More displacement ND entries than node_coordinates.")
                    break

                node_id = ordered_node_ids[index]
                nd = int(nd_elem)
                d_values = [0.0] * 7

                if nd > 0:
                    try:
                        dformat_elem = dformat_tags[dformat_index]
                        for i in range(min(nd, 7)):
                            d_values[i] = float(dformat_elem.D[i])
                        dformat_index += 1  # Only advance when Dformat is used
                    except Exception as e:
                        logging.warning(f"Error reading Dformat for node {node_id}: {e}")

                # if ND == 0, d_values remains all zeros
                displacement_data.append((node_id, timestamp_id, *d_values))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO node_displacements
                (node_id, timestamp_id, D1, D2, D3, D4, D5, D6, D7)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", displacement_data)

        logging.info(f"Inserted {len(displacement_data)} node displacement entries.")

    def get_ordered_beam_ids(self):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT beam_id FROM beam_nodes ORDER BY id ASC")
            return [row[0] for row in cur.fetchall()]

    def store_beam_forces(self, root):
        beam_forces = []
        beam_id_list = self.get_ordered_beam_ids()

        for step in root.SAFIR_RESULTS.STEP:
            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            if hasattr(step, "MNV"):
                for i, bm in enumerate(step.MNV.BM):
                    if i >= len(beam_id_list):
                        logging.warning("More <BM> entries than beam_nodes.")
                        break

                    beam_id = beam_id_list[i]  # map by order
                    for gp_index, gs in enumerate(bm.GS, start=1):
                        beam_forces.append((
                            timestamp_id,
                            beam_id,
                            gp_index,
                            float(getattr(gs, "N", 0)),
                            float(getattr(gs, "Mz", 0)),
                            float(getattr(gs, "My", 0)),
                            float(getattr(gs, "Mw", 0)),
                            float(getattr(gs, "Mr2", 0)),
                            float(getattr(gs, "Vz", 0)),
                            float(getattr(gs, "Vy", 0))
                        ))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO beam_forces
                (timestamp_id, beam_id, gauss_point, N, Mz, My, Mw, Mr2, Vz, Vy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", beam_forces)

        logging.info(f"Inserted {len(beam_forces)} beam force entries using ordered beam_ids.")

    def store_shell_strains(self, root):
        shell_strains = []
        for step in root.SAFIR_RESULTS.STEP:
            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            if hasattr(step, "DSHELL"):
                for elem in step.DSHELL.ELEM:
                    shell_id = int(getattr(elem, "NSH", 0))
                    for area in elem.AREA:
                        nga = int(getattr(area, "NGA", 0))
                        for thick in getattr(area, "THICKNESS", []):
                            ngt = int(getattr(thick, "NGT", 0))
                            Sx, Sy, Sz = self.parse_vector3(thick.STRESS)
                            Px, Py, Pz = self.parse_vector3(thick.STRAIN)
                            Dx, Dy, Dz = self.parse_vector3(thick.D)
                            shell_strains.append((
                                timestamp_id, shell_id, nga, ngt,
                                Sx, Sy, Sz, Px, Py, Pz, Dx, Dy, Dz
                            ))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO shell_strains
                (timestamp_id, shell_id, integration_point, thickness,
                 Sx, Sy, Sz, Px, Py, Pz, Dx, Dy, Dz)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", shell_strains)
        logging.info(f"Inserted {len(shell_strains)} shell strain entries.")

    def store_rebar_strains(self, root):
        rebar_strains = []

        for step in root.SAFIR_RESULTS.STEP:
            if not hasattr(step, "DSHELL"):
                continue

            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            for elem in step.DSHELL.ELEM:
                shell_id = int(getattr(elem, "NSH", 0))

                for area in elem.AREA:
                    nga = int(getattr(area, "NGA", 0))

                    if hasattr(area, "BARS"):
                        bars = area.BARS
                        nbar_tags = bars.findall("NBAR")
                        eps_tags = bars.findall("eps_S")

                        for nbar, eps in zip(nbar_tags, eps_tags):
                            try:
                                rebar_id = int(nbar)
                                eps_sx, eps_sy = self.parse_vector2(str(eps))

                                rebar_strains.append((
                                    timestamp_id,
                                    shell_id,
                                    nga,
                                    rebar_id,
                                    eps_sx,
                                    eps_sy
                                ))
                            except Exception as e:
                                logging.warning(f"Error parsing rebar strain: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO rebar_strains
                (timestamp_id, shell_id, nga, rebar_id, eps_sx, eps_sy)
                VALUES (?, ?, ?, ?, ?, ?)""", rebar_strains)

        logging.info(f"Inserted {len(rebar_strains)} rebar strain entries.")

    def store_fire_curve(self, fct_file_path):
        if not os.path.exists(fct_file_path):
            logging.error(f"Fire curve file not found: {fct_file_path}")
            return

        with open(fct_file_path, "r") as file:
            lines = file.readlines()

        data = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 2:
                try:
                    time = float(parts[0])
                    temp = float(parts[1])
                    data.append((time, temp))
                except ValueError:
                    continue

        if not data:
            logging.warning("No valid data in fire curve file.")
            return

        df = pd.DataFrame(data, columns=["time", "temperature"])
        df.insert(0, "id", range(1, len(df) + 1))

        with self.db.connect() as conn:
            conn.execute("DELETE FROM Time_temperature_curve")
            df.to_sql("Time_temperature_curve", conn, if_exists="append", index=False)

        logging.info(f"Inserted {len(df)} records into Time_temperature_curve.")

    def insert_timestamp(self, time_val):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO timestamps (time) VALUES (?)", (time_val,))
            cur.execute("SELECT id FROM timestamps WHERE time = ?", (time_val,))
            return cur.fetchone()[0]

    def parse_vector2(self, text):
        try:
            parts = text.strip().split()
            return float(parts[0]), float(parts[1])
        except:
            return None, None

    def parse_vector3(self, text_element):
        try:
            parts = str(text_element).strip().split()
            return float(parts[0]), float(parts[1]), float(parts[2])
        except:
            return None, None, None


if __name__ == "__main__":
    #db_path = input("Enter SQLite database path: ").strip()
    #xml_path = input("Enter SAFIR XML file path: ").strip()

    db_path = 'rectslabwcol.db'
    xml_path = 'rectslabwcol.xml'
    fct_path = 'data/S1C.fct'
    db = DatabaseManager(db_path)
    parser = FileParser(db)

    db.clear_database()
    parser.parse_xml_data(xml_path)
    parser.store_fire_curve(fct_path)
    db.create_views()
