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

            CREATE TABLE IF NOT EXISTS temperature_curve (
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
                y REAL
            );

            CREATE TABLE IF NOT EXISTS solid_mesh (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solid_id INTEGER NOT NULL,
                N1 INTEGER, N2 INTEGER, N3 INTEGER, N4 INTEGER,
                material_tag INTEGER
            );

            CREATE TABLE IF NOT EXISTS frontiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solid_id INTEGER NOT NULL,
                face1 TEXT DEFAULT 'NO',
                face2 TEXT DEFAULT 'NO',
                face3 TEXT DEFAULT 'NO',
                face4 TEXT DEFAULT 'NO'
            );

            CREATE TABLE IF NOT EXISTS material_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_tag INTEGER NOT NULL,
                material_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS node_temperatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_id INTEGER NOT NULL,
                node_id INTEGER NOT NULL,
                Temperature REAL DEFAULT 20
            );

            """)
            logging.info("Database tables ensured.")


    # def create_views(self):
    #     with self.connect() as conn:
    #         cursor = conn.cursor()
    #         cursor.executescript("""
    #         DROP VIEW IF EXISTS beam_section_lookup;
    #         CREATE VIEW beam_section_lookup AS
    #         SELECT
    #             bn.beam_id AS beam_id,
    #             bs.section AS section
    #         FROM
    #             beam_nodes bn
    #         JOIN
    #             beam_section bs ON bn.beam_tag = bs.beam_tag;
    #
    #         DROP VIEW IF EXISTS shell_section_lookup;
    #         CREATE VIEW shell_section_lookup AS
    #         SELECT
    #             sn.shell_id AS shell_id,
    #             ss.section AS section
    #         FROM
    #             shell_nodes sn
    #         JOIN
    #             shell_section ss ON sn.shell_tag = ss.shell_tag;
    #
    #         """)
    #         logging.info("Views created.")

    def clear_database(self):
        # confirm = input("Are you sure you want to clear the database? (yes/no): ")
        # if confirm.lower() != 'yes':
        #     logging.info("Database clearing aborted.")
        #     return
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.executescript("""            
            DELETE FROM temperature_curve;
            DELETE FROM model_data;
            DELETE FROM timestamps;
            DELETE FROM node_coordinates;
            DELETE FROM solid_mesh;
            DELETE FROM frontiers;
            DELETE FROM material_list;
            DELETE FROM node_temperatures;
            
            DELETE FROM sqlite_sequence WHERE name='temperature_curve';
            DELETE FROM sqlite_sequence WHERE name='model_data';
            DELETE FROM sqlite_sequence WHERE name='timestamps';
            DELETE FROM sqlite_sequence WHERE name='node_coordinates';
            DELETE FROM sqlite_sequence WHERE name='solid_mesh';
            DELETE FROM sqlite_sequence WHERE name='frontiers';
            DELETE FROM sqlite_sequence WHERE name='material_list';
            DELETE FROM sqlite_sequence WHERE name='node_temperatures';
            
            DROP VIEW IF EXISTS vw_solid_avg_temperature;
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
        self.store_solid_mesh(root)
        self.store_frontiers(root)
        self.store_material_list(root)
        self.store_node_temperatures(root)
    def store_model_data(self, root):
        # SAFIR tag -> description mapping
        metadata_map = {
            "NNODE": "Number of Nodes",
            "NDIM": "Number of Dimensions",
            "NDOFMAX": "Number of Degrees of Freedom",
            "TYPE": "Analysis Type",
            "NS": "Number of Solids",
            "NM": "Number of Material Types",
            "NSOLS": "Number of Solids Types",
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
        for node_id, node in enumerate(nodes, start=1):
            try:
                x = float(node.P1)
                y = float(node.P2)
                node_data.append((node_id, x, y))
            except Exception as e:
                logging.warning(f"Error parsing node {node_id}: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            # Adjusted to use three placeholders matching (node_id, x, y)
            cur.executemany("""
                INSERT INTO node_coordinates (node_id, x, y)
                VALUES (?, ?, ?)
            """, node_data)
        logging.info(f"Inserted {len(node_data)} node coordinates.")

    def store_solid_mesh(self, root):
        solids = root.SAFIR_RESULTS.SOLIDS.S
        solid_data = []
        for solid_id, solid in enumerate(solids, start=1):
            try:
                # Get all <N> tags (there should be at least 4)
                n_tags = solid.findall("N")
                if len(n_tags) < 4:
                    logging.warning(f"Solid {solid_id} has less than 4 node entries; skipping.")
                    continue
                N1 = int(n_tags[0].text.strip())
                N2 = int(n_tags[1].text.strip())
                N3 = int(n_tags[2].text.strip())
                N4 = int(n_tags[3].text.strip())
                # Get the material tag from the <MS> element
                MS_elem = solid.find("MS")
                if MS_elem is None:
                    logging.warning(f"Solid {solid_id} missing material tag; defaulting to 0.")
                    material_tag = 0
                else:
                    material_tag = int(MS_elem.text.strip())
                solid_data.append((solid_id, N1, N2, N3, N4, material_tag))
            except Exception as e:
                logging.warning(f"Error parsing solid {solid_id}: {e}")
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO solid_mesh (solid_id, N1, N2, N3, N4, material_tag)
                VALUES (?, ?, ?, ?, ?, ?)
            """, solid_data)
        logging.info(f"Inserted {len(solid_data)} solid mesh records.")

    def store_frontiers(self, root):
        # Check for the FRONTIERS section within SAFIR_RESULTS
        if not hasattr(root.SAFIR_RESULTS, "FRONTIERS"):
            logging.warning("No <FRONTIERS> section found.")
            return

        frontier_elements = root.SAFIR_RESULTS.FRONTIERS.S
        frontier_data = []
        for s in frontier_elements:
            try:
                solid_id = int(s.NSOL.text.strip())
            except Exception as e:
                logging.warning(f"Error parsing NSOL in frontiers: {e}")
                continue

            # Initialize all faces as "NO"
            face1, face2, face3, face4 = "NO", "NO", "NO", "NO"
            if hasattr(s, "F"):
                f_text = s.F.text.strip()
                tokens = f_text.split()
                if len(tokens) >= 2:
                    try:
                        face_number = int(tokens[0])
                        face_value = tokens[1]
                        if face_number == 1:
                            face1 = face_value
                        elif face_number == 2:
                            face2 = face_value
                        elif face_number == 3:
                            face3 = face_value
                        elif face_number == 4:
                            face4 = face_value
                        else:
                            logging.warning(f"Face number {face_number} is out of range for solid {solid_id}.")
                    except Exception as e:
                        logging.warning(f"Error parsing face tokens for solid {solid_id}: {e}")
            else:
                logging.warning(f"No <F> element found for solid {solid_id}; defaulting faces to NO.")

            frontier_data.append((solid_id, face1, face2, face3, face4))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO frontiers (solid_id, face1, face2, face3, face4)
                VALUES (?, ?, ?, ?, ?)
            """, frontier_data)
        logging.info(f"Inserted {len(frontier_data)} frontier records.")

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
                VALUES (?, ?)
            """, material_data)
        logging.info(f"Inserted {len(material_data)} materials into material_list.")

    def get_ordered_node_ids(self):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT node_id FROM node_coordinates ORDER BY id ASC")
            return [row[0] for row in cur.fetchall()]

    def store_node_temperatures(self, root):
        # This function reads temperature data for each step and stores it in 'node_temperatures'
        temperature_data = []
        ordered_node_ids = self.get_ordered_node_ids()

        # Iterate over each analysis step; assume each <STEP> contains <TIME> and a <TEMPERATURES> section with <T> elements.
        for step in root.SAFIR_RESULTS.STEP:
            if not hasattr(step, "TEMPERATURES"):
                logging.warning("No TEMPERATURES data found in STEP; skipping.")
                continue

            try:
                timestep = float(step.TIME.pyval)
            except Exception as e:
                logging.warning(f"Error parsing time for STEP: {e}")
                continue

            timestamp_id = self.insert_timestamp(timestep)
            t_tags = step.TEMPERATURES.findall("T")

            for index, t_elem in enumerate(t_tags):
                if index >= len(ordered_node_ids):
                    logging.warning("More temperature entries than node coordinates.")
                    break
                node_id = ordered_node_ids[index]
                try:
                    temp_val = float(t_elem)
                except Exception as e:
                    logging.warning(f"Error parsing temperature for node {node_id}: {e}")
                    temp_val = 20.0  # Default value if error occurs

                temperature_data.append((timestamp_id, node_id, temp_val))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO node_temperatures (timestamp_id, node_id, Temperature)
                VALUES (?, ?, ?)
            """, temperature_data)
        logging.info(f"Inserted {len(temperature_data)} node temperature entries.")


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
            conn.execute("DELETE FROM temperature_curve")
            df.to_sql("temperature_curve", conn, if_exists="append", index=False)

        logging.info(f"Inserted {len(df)} records into temperature_curve.")

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

class PostProcessor:
    def __init__(self, db_manager):
        self.db = db_manager

    def calc_maxtemp_bymaterial(self):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE VIEW vw_solid_avg_temperature AS
            WITH solid_nodes AS (
                SELECT solid_id, material_tag, N1 AS node_id FROM solid_mesh WHERE N1 IS NOT NULL
                UNION ALL
                SELECT solid_id, material_tag, N2 FROM solid_mesh WHERE N2 IS NOT NULL
                UNION ALL
                SELECT solid_id, material_tag, N3 FROM solid_mesh WHERE N3 IS NOT NULL
                UNION ALL
                SELECT solid_id, material_tag, N4 FROM solid_mesh WHERE N4 IS NOT NULL
            )
            SELECT 
                sn.material_tag,
                tc.timestamp_id,
                AVG(tc.Temperature) AS avg_temperature
            FROM solid_nodes sn
            JOIN node_temperatures tc ON sn.node_id = tc.node_id
            GROUP BY sn.material_tag, tc.timestamp_id;
            """)
            logging.info("Created temperature by material curve.")

def batch_process_folder(xml_folder, fct_path):
    # Check fire curve exists
    if not os.path.isfile(fct_path):
        logging.error(f"Fire curve file not found: {fct_path}")
        return

    # List all XML files in folder
    xml_files = [f for f in os.listdir(xml_folder) if f.lower().endswith(".xml")]

    if not xml_files:
        logging.warning("No XML files found in folder.")
        return

    logging.info(f"Found {len(xml_files)} XML files to process.")

    for xml_file in xml_files:
        xml_path = os.path.join(xml_folder, xml_file)
        db_name = os.path.splitext(xml_file)[0] + ".db"
        db_path = os.path.join(xml_folder, db_name)

        logging.info(f"Processing {xml_file} -> {db_name}")

        try:
            db = DatabaseManager(db_path)
            parser = FileParser(db)
            postprocessor = PostProcessor(db)

            db.clear_database()
            parser.parse_xml_data(xml_path)
            parser.store_fire_curve(fct_path)
            postprocessor.calc_maxtemp_bymaterial()

        except Exception as e:
            logging.error(f"Failed to process {xml_file}: {e}")

def store_node_coords_per_file(output_db_path, xml_folder):
    from lxml import objectify

    if not os.path.exists(xml_folder):
        logging.error(f"Folder not found: {xml_folder}")
        return

    xml_files = [f for f in os.listdir(xml_folder) if f.lower().endswith(".xml")]
    if not xml_files:
        logging.warning("No XML files found.")
        return

    logging.info(f"Processing {len(xml_files)} XML files into {output_db_path}")
    conn = sqlite3.connect(output_db_path)
    cursor = conn.cursor()

    for xml_file in xml_files:
        xml_path = os.path.join(xml_folder, xml_file)
        table_name = os.path.splitext(xml_file)[0].replace(".", "_").replace("-", "_")

        logging.info(f"Processing {xml_file} -> Table: {table_name}")
        try:
            with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f"<ROOT>{f.read()}</ROOT>"
            root = objectify.fromstring(content)

            nodes = root.SAFIR_RESULTS.NODES.N
            data = []
            for node_id, node in enumerate(nodes, start=1):
                try:
                    x = float(node.P1)
                    y = float(node.P2)
                    data.append((node_id, x, y))
                except Exception as e:
                    logging.warning(f"Error parsing node {node_id} in {xml_file}: {e}")

            # Create table if not exists (drop if exists to ensure fresh insert)
            cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")
            cursor.execute(f"""
                CREATE TABLE [{table_name}] (
                    fiber_index INTEGER PRIMARY KEY,
                    x REAL,
                    y REAL
                )
            """)
            cursor.executemany(
                f"INSERT INTO [{table_name}] (fiber_index, x, y) VALUES (?, ?, ?)",
                data
            )
            conn.commit()
            logging.info(f"Inserted {len(data)} fibers into {table_name}")

        except Exception as e:
            logging.error(f"Failed to process {xml_file}: {e}")

    conn.close()
    logging.info("All files processed.")

if __name__ == "__main__":
    input_folder = "BatchXml/Beams"  # Folder containing all XMLs
    fct_file = "data/S1C.fct"  # Shared fire curve file

    # batch_process_folder(input_folder, fct_file)
    # db_path = input("Enter SQLite database path: ").strip()
    store_node_coords_per_file(db_path,input_folder)

    # xml_path = input("Enter SAFIR XML file path: ").strip()

    # db_path = 'W24.db'
    # xml_path = 'w24x55_ins.XML'
    # fct_path = 'data/S1C.fct'

    # db = DatabaseManager(db_path)
    # parser = FileParser(db)
    # postprocessor = PostProcessor(db)

    # db.clear_database()
    # parser.parse_xml_data(xml_path)
    # parser.store_fire_curve(fct_path)
    # postprocessor.calc_maxtemp_bymaterial()
    # db.create_views()
