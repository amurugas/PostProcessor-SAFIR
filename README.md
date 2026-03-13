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
├── SAFIR-Dashboard/                 # Dashboard apps (Streamlit + Bokeh)
│   ├── Streamlit.py                 # Simple upload-based Streamlit dashboard
│   ├── streamlitv2.py               # Advanced 2-D thermal Streamlit dashboard
│   └── bokeh_app/                   # High-performance Bokeh server dashboard
│       ├── cache_db.py              # Temp SQLite cache DB lifecycle
│       ├── data_loader.py           # Cache DB → DataFrame queries
│       ├── plots.py                 # Bokeh figure builders
│       ├── main.py                  # Bokeh curdoc() entry point
│       └── server.py                # CLI launcher (cache + bokeh serve)
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

#### Streamlit apps (legacy)

| Script | Description |
|---|---|
| `SAFIR-Dashboard/Streamlit.py` | Simple upload-based dashboard |
| `SAFIR-Dashboard/streamlitv2.py` | Advanced 2-D thermal section viewer |

```bash
streamlit run SAFIR-Dashboard/Streamlit.py
# or
streamlit run SAFIR-Dashboard/streamlitv2.py
```

#### Bokeh app (recommended)

A high-performance Bokeh server dashboard located in
`SAFIR-Dashboard/bokeh_app/`.  It uses a **temporary cache database** to
keep the source `.db` file untouched and deliver fast, low-latency charts.

**Architecture**

```
server.py
  │  1. CacheDatabase.build()  →  temp SQLite copy of source DB
  │  2. bokeh serve main.py    →  Bokeh server process
  │       ├─ DataLoader        →  queries cache DB → DataFrames
  │       ├─ plots.*           →  pure Bokeh figure builders
  │       └─ curdoc()          →  widgets + callbacks
  └─ CacheDatabase.close()     →  delete temp DB on exit

Tabs
  ├─ Section Viewer   – 2-D thermal colour-map of cross-section
  ├─ Material Summary – avg / max temperature per material vs. time
  └─ Node History     – single-node temperature history + fire curve
```

**Module overview**

| File | Responsibility |
|---|---|
| `bokeh_app/cache_db.py` | Build & teardown the temporary SQLite cache DB |
| `bokeh_app/data_loader.py` | Execute queries against the cache DB |
| `bokeh_app/plots.py` | Pure Bokeh figure builders (section, material, node) |
| `bokeh_app/main.py` | Bokeh `curdoc()` document – widgets & callbacks |
| `bokeh_app/server.py` | CLI launcher: cache lifecycle + `bokeh serve` |

**Usage**

```bash
# Recommended: use the server launcher
python SAFIR-Dashboard/bokeh_app/server.py --db path/to/results.db

# Custom port / no browser
python SAFIR-Dashboard/bokeh_app/server.py \
    --db path/to/results.db \
    --port 5007 \
    --no-browser

# Advanced: run bokeh serve directly (set env var manually)
export SAFIR_CACHE_DB=/tmp/safir_cache_xxx.db
bokeh serve SAFIR-Dashboard/bokeh_app/main.py --show
```

The temporary cache database is automatically **deleted** when the server
process exits (whether by Ctrl-C or closing the browser).

---

## FastAPI Web Shell

A lightweight web front-end built with **FastAPI** that wraps the existing
Bokeh structural viewer.

**What it adds**

- A browser landing page at `http://localhost:8000`
- A case-picker dropdown (scans a local folder for `.db` files)
- The selected SAFIR case is passed to the Bokeh server, which renders the
  interactive plots inside the same page

**Stack**

| Component | Role | Port |
|-----------|------|------|
| FastAPI | Landing page, case picker | 8000 |
| Bokeh Server | Interactive plots | 5006 |
| SQLite | Case data | – |

### Folder layout

Arrange your SAFIR cases like this:

```
%USERPROFILE%\SAFIR\Cases\
    Case_001\Raw.db
    Case_002\Raw.db
    Case_003\Raw.db
```

Each sub-folder must contain exactly one `*.db` SQLite file built from your
SAFIR structural results.  The path can be anywhere on disk; update
`SAFIR_CASES_DIR` in `launch_fastapi.bat` (or set the env var) to point to it.

### Running on Windows

**Step 1 – install dependencies** (one-time)

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

**Step 2 – edit the cases path** in `launch_fastapi.bat`:

```bat
SET SAFIR_CASES_DIR=D:\SAFIR\Cases
```

**Step 3 – start the Bokeh server** (first terminal):

```bat
launch_bokeh.bat
```

**Step 4 – start FastAPI** (second terminal):

```bat
launch_fastapi.bat
```

**Step 5 – open the browser**:

```
http://localhost:8000
```

Select a case from the dropdown.  The Bokeh plots load below the header.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFIR_CASES_DIR` | `~/SAFIR/Cases` | Root folder scanned for cases |
| `BOKEH_URL` | `http://localhost:5006/app` | Bokeh server URL |
| `SAFIR_DB_PATH` | `Raw.db` | Fallback DB for standalone Bokeh use |

### Manual launch (without .bat files)

```bat
REM Terminal 1 – Bokeh
.venv\Scripts\bokeh serve viewer\app.py ^
    --port 5006 ^
    --allow-websocket-origin=*

REM Terminal 2 – FastAPI
set SAFIR_CASES_DIR=D:\SAFIR\Cases
.venv\Scripts\uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
```

---



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
