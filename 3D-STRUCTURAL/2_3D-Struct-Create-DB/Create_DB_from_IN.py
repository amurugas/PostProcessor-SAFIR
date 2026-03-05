import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SafirDB:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        self.beam_group_map = {}
        self.shell_group_map = {}

    def clear_database(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            DELETE FROM beams;
            DELETE FROM beam_groups;
            DELETE FROM shells;
            DELETE FROM shell_groups;
            DELETE FROM nodes;
        """)
        self.conn.commit()
        logging.info("Database cleared.")

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY,
                x REAL,
                y REAL,
                z REAL
            );

            CREATE TABLE IF NOT EXISTS beam_groups (
                id INTEGER PRIMARY KEY,
                section TEXT
            );

            CREATE TABLE IF NOT EXISTS beams (
                id INTEGER PRIMARY KEY,
                node1 INTEGER,
                node3 INTEGER,
                node2 INTEGER,
                node4 INTEGER,
                group_id INTEGER,
                FOREIGN KEY(group_id) REFERENCES beam_groups(id)
            );

            CREATE TABLE IF NOT EXISTS shell_groups (
                id INTEGER PRIMARY KEY,
                section TEXT
            );

            CREATE TABLE IF NOT EXISTS shells (
                id INTEGER PRIMARY KEY,
                node1 INTEGER,
                node2 INTEGER,
                node3 INTEGER,
                node4 INTEGER,
                group_id INTEGER,
                FOREIGN KEY(group_id) REFERENCES shell_groups(id)
            );
        """)
        self.conn.commit()
        logging.info("Tables created.")

    def insert_node(self, node_id, x, y, z):
        self.conn.execute("INSERT OR IGNORE INTO nodes VALUES (?, ?, ?, ?)", (node_id, x, y, z))

    def insert_beam_group(self, group_id, section):
        self.conn.execute("INSERT INTO beam_groups (id, section) VALUES (?, ?)", (group_id, section))
        self.beam_group_map[group_id] = section

    def insert_shell_group(self, group_id, section):
        self.conn.execute("INSERT INTO shell_groups (id, section) VALUES (?, ?)", (group_id, section))
        self.shell_group_map[group_id] = section

    def insert_beam(self, beam_id, n1, n3, n2, n4, group_id):

        self.conn.execute("INSERT INTO beams VALUES (?, ?, ?, ?, ?, ?)", (beam_id, n1, n3, n2, n4, group_id))

    def insert_shell(self, shell_id, n1, n2, n3, n4, group_id):
        self.conn.execute("INSERT INTO shells VALUES (?, ?, ?, ?, ?, ?)", (shell_id, n1, n2, n3, n4, group_id))

    def commit(self):
        self.conn.commit()

    def export_for_rhino(self, output_dir="exports"):
        import os
        os.makedirs(output_dir, exist_ok=True)

        def write_csv(filename, headers, rows):
            with open(os.path.join(output_dir, filename), 'w') as f:
                f.write(",".join(headers) + "\n")
                for row in rows:
                    f.write(",".join(map(str, row)) + "\n")

        # Export Nodes
        cur = self.conn.cursor()
        cur.execute("SELECT id, x, y, z FROM nodes ORDER BY id")
        write_csv("nodes.txt", ["NodeID", "X", "Y", "Z"], cur.fetchall())

        # Export Beams
        cur.execute("""
            SELECT b.id, b.node1, b.node3, b.node2, b.node4, g.section 
            FROM beams b
            JOIN beam_groups g ON b.group_id = g.id
            ORDER BY b.id
        """)
        write_csv("beams.txt", ["BeamID", "Node1", "Node3", "Node2", "Node4", "Section"], cur.fetchall())

        # Export Shells
        cur.execute("""
            SELECT s.id, s.node1, s.node2, s.node3, s.node4, g.section
            FROM shells s
            JOIN shell_groups g ON s.group_id = g.id
            ORDER BY s.id
        """)
        write_csv("shells.txt", ["ShellID", "Node1", "Node2", "Node3", "Node4", "Section"], cur.fetchall())

        logging.info(f"Exported files written to '{output_dir}' directory.")

def parse_input_file(file_path, db: SafirDB):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    mode = None
    beam_group_counter = 1
    shell_group_counter = 1

    for line in lines:
        line = line.strip()

        if line.startswith("NODES"):
            mode = "NODES"
            continue
        elif line.startswith("NODOFBEAM"):
            mode = "NODOFBEAM"
            continue
        elif line.startswith("NODOFSHELL"):
            mode = "NODOFSHELL"
            continue
        elif line.startswith("ELEM"):
            # Check which element type we are in
            if mode == "NODOFBEAM":
                mode = "BEAMS"
            elif mode == "NODOFSHELL":
                mode = "SHELLS"

        if mode == "NODES" and line.startswith("NODE"):
            _, nid, x, y, z = line.split()
            db.insert_node(int(nid), float(x), float(y), float(z))

        elif mode == "NODOFBEAM":
            if line.endswith(".TEM"):
                section = line.split(".TEM")[0].strip()
                db.insert_beam_group(beam_group_counter, section)
                beam_group_counter += 1

        elif mode == "NODOFSHELL":
            if line.endswith(".TSH"):
                section = line.split(".TSH")[0].strip()
                db.insert_shell_group(shell_group_counter, section)
                shell_group_counter += 1

        elif mode == "BEAMS" and line.startswith("ELEM"):
            parts = line.split()
            _, eid, n1, n3, n2, n4, group_id = parts
            db.insert_beam(int(eid), int(n1), int(n3), int(n2), int(n4), int(group_id))

        elif mode == "SHELLS" and line.startswith("ELEM"):
            parts = line.split()
            _, eid, n1, n2, n3, n4, group_id = parts
            db.insert_shell(int(eid), int(n1), int(n2), int(n3), int(n4), int(group_id))

    db.commit()
    logging.info("Parsing complete and data committed.")


if __name__ == "__main__":
    db = SafirDB("safir_input.db")
    db.clear_database()
    parse_input_file("output/Slab_S2A.IN", db)
    db.export_for_rhino()
