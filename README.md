# PostProcessor-SAFIR

Python post-processing tools for [SAFIR](https://www.uee.uliege.be/cms/c_4016728/en/uee-safir) structural fire analysis results.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/amurugas/PostProcessor-SAFIR.git
cd PostProcessor-SAFIR

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install shared dependencies
pip install -r requirements-base.txt

# (Optional) Install in editable mode so `import shared` works anywhere
pip install -e .
```

---

## Project Structure

```
PostProcessor-SAFIR/
├── shared/                          # Reusable utilities
│   ├── database/
│   │   ├── base.py                  # Abstract database manager
│   │   ├── thermal_db.py            # 2D-thermal DB manager
│   │   └── structural_db.py         # 3D-structural DB manager
│   ├── utils/
│   │   ├── config.py                # Config (env-var backed)
│   │   ├── logger.py                # Logging setup
│   │   ├── validators.py            # Path / file validators
│   │   └── formatters.py            # Unit conversions & formatting
│   ├── visualization/
│   │   ├── base_viewer.py           # Abstract viewer base class
│   │   ├── color_schemes.py         # Shared colour palettes
│   │   └── export_utils.py          # CSV / Excel export helpers
│   └── data/
│       ├── parsers.py               # FireCurveParser, XmlParser
│       └── processors.py            # TemperatureProcessor, DisplacementProcessor
│
├── 2D-THERMAL/                      # 2-D thermal analysis tools
│   ├── 2_2D-Thermal-Create-DB/      # Build SQLite DB from XML
│   ├── 4_2D-Thermal-Bokeh-Dashboard/# Interactive Bokeh dashboard
│   └── 5_2D-Thermal-Rhino-Visualizer/# CSV export for Rhino
│
├── 3D-STRUCTURAL/                   # 3-D structural analysis tools
│   ├── 2_3D-Struct-Create-DB/       # Build SQLite DB from XML / IN
│   ├── 4_3D-Struct-Rhino-Movie/     # Rhino animation CSV export
│   ├── 5_3D-Struct-Beam-Forces-Viewer/
│   ├── 6_3D-Struct-Node-Displacement-Viewer/
│   ├── 7_3D-Struct-Beam-FiberStress/
│   ├── 8_3D-Struct-Slab-MohrStress-Plotter/
│   └── 9_3D-Struct-Slab-Stress-Plotter/
│
├── SAFIR-Dashboard/                 # Streamlit multi-tool dashboard
│
├── docs/
│   ├── ARCHITECTURE.md              # Module relationships & data flow
│   ├── CONTRIBUTING.md              # Dev guidelines
│   └── API.md                       # Shared API reference
│
├── .env.example                     # Config template
├── requirements-base.txt            # Runtime dependencies
├── requirements-dev.txt             # Dev dependencies
├── setup.py                         # Package setup (editable install)
└── Makefile                         # Common dev tasks
```

---

## Tools

### 2D-THERMAL

| Folder | Script | What it does |
|---|---|---|
| `2_2D-Thermal-Create-DB` | `2D-Thermal-CreateDB.py` | Parse SAFIR XML → SQLite |
| `4_2D-Thermal-Bokeh-Dashboard` | `2D-Thermal-Bokeh.py` | Interactive Bokeh dashboard |
| `5_2D-Thermal-Rhino-Visualizer` | `2DBeamRender_CSV.py` | Export mesh+temperature CSVs for Rhino |

### 3D-STRUCTURAL

| Folder | Script | What it does |
|---|---|---|
| `2_3D-Struct-Create-DB` | `Create_DB_from_XML.py` | Parse SAFIR XML → SQLite |
| `5_3D-Struct-Beam-Forces-Viewer` | `1_Beam_StressPlot_Bokeh.py` | Beam force plots |
| `6_3D-Struct-Node-Displacement-Viewer` | `1_Extract_Node_Disp.py` + `2_Disp_Plot_Bokeh.py` | Node displacement time-series |
| `8_3D-Struct-Slab-MohrStress-Plotter` | `1_MohrStress.py` + `2_MohrStressPlot-Bokeh.py` | Mohr-circle stress visualisation |
| `9_3D-Struct-Slab-Stress-Plotter` | `slab_stress_viewer.py` | Slab stress contour plots |

### SAFIR-Dashboard

A single Streamlit app (`SAFIR-Dashboard/Streamlit.py`) that accepts any SAFIR `.db` file and provides node displacement, beam force, and temperature–time tabs.

```bash
streamlit run SAFIR-Dashboard/Streamlit.py
```

---

## Using the Shared Utilities

```python
from shared.database import StructuralDatabaseManager
from shared.data import FireCurveParser, XmlParser
from shared.data import DisplacementProcessor
from shared.utils import setup_logger, validate_xml_path

logger = setup_logger(__name__)

# 1. Validate inputs
xml_path = validate_xml_path("results/my_model.xml")
fct_path = "results/S1C.fct"

# 2. Create / open the database
db = StructuralDatabaseManager("output/my_model.db")
db.clear_database()

# 3. Parse inputs (existing tool scripts handle the actual INSERT logic)
fire_data = FireCurveParser(fct_path).parse()
root = XmlParser(xml_path).parse()

# 4. Query results
proc = DisplacementProcessor("output/my_model.db")
times, disps = proc.get_displacement_time_series(node_id=5, dof="D2")
logger.info("Max displacement at node 5: %.4f m", max(abs(d) for d in disps))
```

---

## Development

```bash
# Install dev tools
make dev

# Lint the shared package
make lint

# Run tests with coverage
make test
```

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for the full contribution guide and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module map.

---

## Documentation

| Document | Description |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design, module relationships, data flow |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Dev setup, coding standards, PR workflow |
| [docs/API.md](docs/API.md) | Shared API reference |

---

## License

MIT – see `LICENSE` for details.
