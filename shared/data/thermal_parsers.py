import logging
from .parsers import XmlParser

logger = logging.getLogger(__name__)

class ThermalParser(XmlParser):

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

    def parse_and_store_tables(self):
        root = self.parse()
        self.store_model_data(root)
        self.store_node_coordinates(root)
        self.store_solid_mesh(root)
        self.store_frontiers(root)
        self.store_material_list(root)
        self.store_node_temperatures(root)
