# PostProcessor-SAFIR

Python post-processing tools for [SAFIR](https://www.uee.uliege.be/cms/c_4016728/en/uee-safir) structural fire analysis results.

Provides two independent interactive web viewers – one for **2-D thermal** results and one for **3-D structural** results – each with its own FastAPI web shell and Bokeh server.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/amurugas/PostProcessor-SAFIR.git
cd PostProcessor-SAFIR

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Project Structure

```
PostProcessor-SAFIR/
├── apps/
│   ├── thermal_viewer.py        # Bokeh app – 2-D thermal results (port 5006)
│   ├── structural_viewer.py     # Bokeh app – 3-D structural results (port 5007)
│   ├── fastapi_thermal.py       # FastAPI web shell – thermal viewer (port 8000)
│   ├── fastapi_structural.py    # FastAPI web shell – structural viewer (port 8001)
│   └── fastapi_shell.py         # Legacy combined shell (kept for reference)
│
├── database/
│   ├── queries_thermal.py       # SQL queries for thermal viewer
│   └── queries_structural.py    # SQL queries for structural viewer
│
├── templates/
│   ├── thermal.html             # Landing page for thermal viewer
│   ├── structural.html          # Landing page for structural viewer
│   └── index.html               # Legacy combined template
│
├── shared/                      # Reusable utilities
│   ├── database/
│   │   ├── base.py              # Abstract database manager
│   │   ├── thermal_db.py        # 2-D thermal DB manager
│   │   └── structural_db.py     # 3-D structural DB manager
│   ├── utils/
│   │   ├── config.py            # Config (env-var backed)
│   │   ├── logger.py            # Logging setup
│   │   ├── validators.py        # Path / file validators
│   │   └── formatters.py        # Unit conversions & formatting
│   ├── visualization/
│   │   ├── base_viewer.py       # Abstract viewer base class
│   │   ├── color_schemes.py     # Shared colour palettes
│   │   └── export_utils.py      # CSV / Excel export helpers
│   └── data/
│       ├── parsers.py           # FireCurveParser, XmlParser
│       ├── processors.py        # TemperatureProcessor, DisplacementProcessor
│       ├── thermal_parsers.py   # 2-D thermal-specific parsers
│       └── structural_parsers.py# 3-D structural-specific parsers
│
├── 2D-THERMAL/                  # 2-D thermal analysis tools
│   ├── 2_2D-Thermal-Create-DB/  # Build SQLite DB from SAFIR XML
│   └── 5_2D-Thermal-Rhino-Visualizer/ # CSV export for Rhino
│
├── 3D-STRUCTURAL/               # 3-D structural analysis tools
│   ├── 2_3D-Struct-Create-DB/   # Build SQLite DB from XML / IN
│   ├── 5_3D-Struct-Beam-Forces-Viewer/
│   ├── 6_3D-Struct-Node-Displacement-Viewer/
│   ├── 7_3D-Struct-Beam-FiberStress/
│   ├── 8_3D-Struct-Slab-MohrStress-Plotter/
│   └── 9_3D-Struct-Slab-Stress-Plotter/
│
├── docs/
│   ├── ARCHITECTURE.md          # Module relationships & data flow
│   ├── CONTRIBUTING.md          # Dev guidelines
│   └── API.md                   # Shared API reference
│
├── tests/                       # Test suite
├── _Archive/                    # Legacy / reference code
│
├── launch_thermal.bat           # ⭐ Start full thermal stack (Windows)
├── launch_structural.bat        # ⭐ Start full structural stack (Windows)
├── launch_all.bat               # Start everything together (Windows)
├── launch.bat                   # Bokeh-only (standalone, no FastAPI)
├── requirements.txt             # All runtime dependencies
└── Makefile                     # Dev automation (lint, test, install)
```

---

## Viewers

### 🌡 Thermal Viewer (2-D)

Displays SAFIR 2-D thermal analysis results:

- **Temperature field** – colour-mapped scatter plot of node temperatures
- **Temperature history** – time-series for any selected node
- Section selector and timestep slider

| Component | URL | Port |
|-----------|-----|------|
| Bokeh server | `http://localhost:5006/thermal_viewer` | 5006 |
| FastAPI shell | `http://localhost:8000` | 8000 |

**Launch (Windows)**

```bat
launch_thermal.bat
```

**Launch (manual)**

```bash
# Terminal 1 – Bokeh thermal server
bokeh serve apps/thermal_viewer.py --port 5006 --allow-websocket-origin=*

# Terminal 2 – FastAPI thermal shell
set SAFIR_CASES_DIR=D:\SAFIR\Cases
uvicorn apps.fastapi_thermal:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in your browser.

---

### 🏗 Structural Viewer (3-D)

Displays SAFIR 3-D structural analysis results:

- **Beam force history** – N, Mz, My, Vz, Vy vs time for any beam
- **Node displacement history** – D1, D2, D3 vs time for any node
- **Fiber result history** – stress or strain vs time per fiber

| Component | URL | Port |
|-----------|-----|------|
| Bokeh server | `http://localhost:5007/structural_viewer` | 5007 |
| FastAPI shell | `http://localhost:8001` | 8001 |

**Launch (Windows)**

```bat
launch_structural.bat
```

**Launch (manual)**

```bash
# Terminal 1 – Bokeh structural server
bokeh serve apps/structural_viewer.py --port 5007 --allow-websocket-origin=*

# Terminal 2 – FastAPI structural shell
set SAFIR_CASES_DIR=D:\SAFIR\Cases
uvicorn apps.fastapi_structural:app --host 0.0.0.0 --port 8001
```

Then open **http://localhost:8001** in your browser.

---

## Running Both Viewers Together

```bat
launch_all.bat
```

This starts all four servers simultaneously:

| Server | Port |
|--------|------|
| Bokeh thermal | 5006 |
| Bokeh structural | 5007 |
| FastAPI thermal | 8000 |
| FastAPI structural | 8001 |

---

## Case Folder Layout

Both FastAPI apps scan a root folder for SAFIR cases. Arrange your cases like this:

```
%USERPROFILE%\SAFIR\Cases\
    Case_001\Raw.db
    Case_002\Raw.db
    Case_003\Raw.db
```

Each sub-folder must contain exactly one `*.db` SQLite file built from your SAFIR results.  Point to this folder by setting the `SAFIR_CASES_DIR` environment variable in the launcher scripts.

---

## Environment Variables

| Variable | Default | Used by |
|----------|---------|---------|
| `SAFIR_CASES_DIR` | `~/SAFIR/Cases` | Both FastAPI shells |
| `BOKEH_THERMAL_URL` | `http://localhost:5006/thermal_viewer` | `fastapi_thermal.py` |
| `BOKEH_STRUCTURAL_URL` | `http://localhost:5007/structural_viewer` | `fastapi_structural.py` |
| `SAFIR_DB_PATH` | `Raw.db` | Bokeh viewers (standalone mode) |
| `LOG_LEVEL` | `INFO` | All apps |

---

## Building the Databases

Before using the viewers, build a SQLite database from your SAFIR results:

### Thermal database

```bash
# Build from SAFIR XML output
python 2D-THERMAL/2_2D-Thermal-Create-DB/2D-Thermal-DB.py path/to/results.xml
```

### Structural database

```bash
# Build from SAFIR XML output
python 3D-STRUCTURAL/2_3D-Struct-Create-DB/3D-Struct-DB.py path/to/results.xml

# Or build from SAFIR .IN file
python 3D-STRUCTURAL/2_3D-Struct-Create-DB/Create_DB_from_IN.py path/to/model.in
```

---

## Shared Utilities (`shared/`)

The `shared/` package provides reusable components used by the viewers and DB builders:

```python
from shared.database import StructuralDatabaseManager, ThermalDatabaseManager
from shared.data import FireCurveParser, XmlParser
from shared.data import DisplacementProcessor, TemperatureProcessor
from shared.utils import setup_logger, validate_xml_path
from shared.visualization import BaseViewer, export_to_csv
```

See [docs/API.md](docs/API.md) for the full API reference.

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

