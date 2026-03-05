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

    def store_beam_fiber_strains(self, root):
        fiber_strains = []

        for step in root.SAFIR_RESULTS.STEP:
            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            if not hasattr(step, "EpsBM"):
                continue

            for bm_block in step.EpsBM:
                try:
                    beam_id = int(bm_block.BM)
                    gauss_point = int(bm_block.NG)
                    nfibers = int(bm_block.NF)
                    strain_values = [float(e) for e in bm_block.EPSformat.E]

                    if len(strain_values) != nfibers:
                        logging.warning(
                            f"Mismatch: NF={nfibers}, but got {len(strain_values)} strain values for Beam {beam_id} GP {gauss_point}")

                    for idx, strain in enumerate(strain_values, start=1):
                        fiber_strains.append((timestamp_id, beam_id, gauss_point, idx, strain))

                except Exception as e:
                    logging.warning(f"Failed to parse EpsBM block: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO beam_fiber_strains
                (timestamp_id, beam_id, gauss_point, fiber_index, strain)
                VALUES (?, ?, ?, ?, ?)
            """, fiber_strains)

        logging.info(f"Inserted {len(fiber_strains)} beam fiber strain entries.")

    def store_beam_fiber_stresses(self, root):
        fiber_stresses = []

        for step in root.SAFIR_RESULTS.STEP:
            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            if not hasattr(step, "StressBM"):
                continue

            for bm_block in step.StressBM:
                try:
                    beam_id = int(bm_block.BM)
                    gauss_point = int(bm_block.NG)
                    nfibers = int(bm_block.NF)
                    stress_values = [float(s) for s in bm_block.Sformat.S]

                    if len(stress_values) != nfibers:
                        logging.warning(
                            f"Mismatch: NF={nfibers}, but got {len(stress_values)} stress values for Beam {beam_id} GP {gauss_point}")

                    for idx, stress in enumerate(stress_values, start=1):
                        fiber_stresses.append((timestamp_id, beam_id, gauss_point, idx, stress))

                except Exception as e:
                    logging.warning(f"Failed to parse StressBM block: {e}")

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO beam_fiber_stresses
                (timestamp_id, beam_id, gauss_point, fiber_index, stress)
                VALUES (?, ?, ?, ?, ?)
            """, fiber_stresses)

        logging.info(f"Inserted {len(fiber_stresses)} beam fiber stress entries.")

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

    def store_reactions(self, root):
        reaction_data = []
        ordered_node_ids = self.get_ordered_node_ids()

        for step in root.SAFIR_RESULTS.STEP:
            timestep = float(step.TIME.pyval)
            timestamp_id = self.insert_timestamp(timestep)

            if not hasattr(step, "REACTIONS"):
                continue

            reactions_block = step.REACTIONS
            nodes = reactions_block.findall("N")
            rblocks = reactions_block.findall("R")

            node_ids = [int(n) for n in nodes]
            reaction_count = int(reactions_block.NR)

            for i, node_id in enumerate(node_ids):
                start_idx = i * reaction_count
                r_values = [float(rblocks[start_idx + j]) if start_idx + j < len(rblocks) else 0.0
                            for j in range(7)]
                reaction_data.append((timestamp_id, node_id, *r_values))

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO reactions
                (timestamp_id, node_id, R1, R2, R3, R4, R5, R6, R7)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", reaction_data)

        logging.info(f"Inserted {len(reaction_data)} reaction entries.")




