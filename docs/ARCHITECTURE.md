# PostProcessor-SAFIR – Architecture Guide

## Overview

PostProcessor-SAFIR is a collection of Python tools for post-processing [SAFIR](https://www.uee.uliege.be/cms/c_4016728/en/uee-safir) finite-element analysis results.  Results are stored in SQLite databases and explored through two independent interactive web viewers – one for 2-D thermal analysis and one for 3-D structural analysis.

---

## Application Architecture

The project is split into **two fully independent viewer stacks**, each consisting of a Bokeh server (plots) and a FastAPI web shell (case picker + embedding).

```
┌─────────────────────────────────────────────────────────────────────┐
│  THERMAL STACK                                                      │
│                                                                     │
│  launch_thermal.bat                                                 │
│      │                                                              │
│      ├─► Bokeh Server (port 5006)                                   │
│      │       apps/thermal_viewer.py                                 │
│      │       └─ database/queries_thermal.py (SQL)                   │
│      │       └─ SQLite .db file (2-D thermal schema)                │
│      │                                                              │
│      └─► FastAPI (port 8000)                                        │
│              apps/fastapi_thermal.py                                │
│              └─ templates/thermal.html                              │
│              └─ embeds Bokeh via server_document()                  │
│                                                                     │
│  Browser → http://localhost:8000                                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  STRUCTURAL STACK                                                   │
│                                                                     │
│  launch_structural.bat                                              │
│      │                                                              │
│      ├─► Bokeh Server (port 5007)                                   │
│      │       apps/structural_viewer.py                              │
│      │       └─ database/queries_structural.py (SQL)                │
│      │       └─ SQLite .db file (3-D structural schema)             │
│      │                                                              │
│      └─► FastAPI (port 8001)                                        │
│              apps/fastapi_structural.py                             │
│              └─ templates/structural.html                           │
│              └─ embeds Bokeh via server_document()                  │
│                                                                     │
│  Browser → http://localhost:8001                                    │
└─────────────────────────────────────────────────────────────────────┘
```

Both stacks are completely independent: they use different ports, different databases, different templates, and can be run separately or together.

---

## Directory Structure

```
PostProcessor-SAFIR/
├── apps/                        ← Web viewer applications
│   ├── thermal_viewer.py        ← Bokeh 2-D thermal app (port 5006)
│   ├── structural_viewer.py     ← Bokeh 3-D structural app (port 5007)
│   ├── fastapi_thermal.py       ← FastAPI thermal shell (port 8000)
│   └── fastapi_structural.py    ← FastAPI structural shell (port 8001)
│
├── database/                    ← SQL query modules
│   ├── queries_thermal.py       ← Thermal DB queries
│   └── queries_structural.py    ← Structural DB queries
│
├── templates/                   ← Jinja2 HTML templates
│   ├── thermal.html             ← Thermal viewer landing page
│   └── structural.html          ← Structural viewer landing page
│
├── shared/                      ← Reusable utilities
│   ├── database/                ← DB managers (abstract + concrete)
│   ├── utils/                   ← Config, logging, validation, formatting
│   ├── visualization/           ← Base viewer, colour schemes, export
│   └── data/                    ← SAFIR parsers and processing pipelines
│
├── 2D-THERMAL/                  ← 2-D thermal analysis tools
├── 3D-STRUCTURAL/               ← 3-D structural analysis tools
└── _Archive/                    ← Legacy / reference code (not maintained)
```

---

## Module Relationships

```
              ┌─────────────────────────────────────┐
              │            shared/                  │
              │  ┌──────────┐  ┌─────────────────┐  │
              │  │ database │  │      utils      │  │
              │  │  base.py │  │  config.py      │  │
              │  │  thermal │  │  logger.py      │  │
              │  │  struct  │  │  validators.py  │  │
              │  └────┬─────┘  │  formatters.py  │  │
              │       │        └─────────────────┘  │
              │  ┌────▼──────────┐  ┌────────────┐  │
              │  │ visualization │  │    data    │  │
              │  │ base_viewer   │  │  parsers   │  │
              │  │ color_schemes │  │  processors│  │
              │  │ export_utils  │  └────────────┘  │
              │  └───────────────┘                  │
              └──────────────────┬──────────────────┘
                                 │ imports
        ┌───────────────────────┼──────────────────────┐
        ▼                        ▼                      ▼
  2D-THERMAL tools       3D-STRUCTURAL tools     Web Viewers (apps/)
```

---

## Data Flow

```
SAFIR simulation
     │
     ▼
.xml + .fct result files
     │
     ├─ shared.data.parsers.XmlParser
     └─ shared.data.parsers.FireCurveParser
            │
            ▼
     shared.database.*DatabaseManager
     (SQLite .db file)
            │
            ├─ database.queries_thermal / queries_structural
            │         (SQL queries → pd.DataFrame)
            │
            ├─ shared.data.processors.*Processor
            │         (aggregations, statistics)
            │
            └─ apps.*_viewer.py (Bokeh)
                      │
                      └─ apps.fastapi_*.py (FastAPI)
                                │
                                └─ Browser (localhost)
```

---

## shared.database

| Class | Purpose |
|---|---|
| `BaseDatabaseManager` | Abstract base – connection helper, `insert_timestamp`, `clear_database` |
| `ThermalDatabaseManager` | 2-D thermal schema: `node_temperatures`, `solid_mesh`, … |
| `StructuralDatabaseManager` | 3-D structural schema: `beam_forces`, `node_displacements`, … |

### Adding a new analysis type

1. Create `shared/database/my_analysis_db.py`.
2. Subclass `BaseDatabaseManager`.
3. Implement `create_tables()` – call `self._create_common_tables(cursor)` first.
4. Implement `_do_clear()` – delete rows in reverse FK order.
5. Export the new class from `shared/database/__init__.py`.

---

## Database Schemas

### 2-D Thermal Schema

| Table | Key Columns |
|-------|-------------|
| `timestamps` | `id`, `time` |
| `node_coordinates` | `node_id`, `x`, `y` |
| `node_temperatures` | `timestamp_id`, `node_id`, `Temperature` |
| `solid_mesh` | `solid_id`, `N1–N4`, `material_tag` |
| `material_list` | `material_tag`, `material_name` |

### 3-D Structural Schema

| Table | Key Columns |
|-------|-------------|
| `timestamps` | `id`, `time` |
| `node_coordinates` | `node_id`, `x`, `y`, `z` |
| `beam_nodes` | `beam_id`, `N1–N4`, `beam_tag` |
| `beam_section` | `beam_tag`, `section` |
| `beam_forces` | `timestamp_id`, `beam_id`, `gauss_point`, `N`, `Mz`, `My`, `Vz`, `Vy` |
| `node_displacements` | `timestamp_id`, `node_id`, `D1–D7` |
| `beam_fiber_stresses` | `timestamp_id`, `beam_id`, `gauss_point`, `fiber_index`, `stress` |
| `beam_fiber_strains` | `timestamp_id`, `beam_id`, `gauss_point`, `fiber_index`, `strain` |

---

## shared.data

| Class | Purpose |
|---|---|
| `FireCurveParser` | Reads SAFIR `.fct` time-temperature files |
| `XmlParser` | Wraps `lxml.objectify` for SAFIR XML result files |
| `TemperatureProcessor` | Max / average temperature statistics (thermal DB) |
| `DisplacementProcessor` | Time-series and peak displacement queries (structural DB) |

---

## shared.visualization

| Symbol | Purpose |
|---|---|
| `BaseViewer` | Abstract base – `build_layout()`, `show()`, `_run_query()` |
| `MATERIAL_COLORS` | 10-colour palette (cyclic per material index) |
| `TEMPERATURE_PALETTE` | 11-stop blue→red palette for temperature maps |
| `DEFAULT_LINE_COLORS` | Sequential colours for time-series plots |
| `export_to_csv()` | Write a DataFrame to CSV |
| `export_to_excel()` | Write a DataFrame to xlsx |

---

## shared.utils

| Symbol | Purpose |
|---|---|
| `Config` | Dataclass reading settings from env-vars (or `.env`) |
| `setup_logger()` | Returns a configured `logging.Logger` |
| `validate_file_exists()` | Raises `ValueError` if path is missing |
| `validate_db_path()` | Raises `ValueError` if parent dir is missing |
| `validate_xml_path()` | Raises `ValueError` if not an `.xml` file |
| `format_value()` | Numeric formatting with optional unit string |
| `scale_n_to_kips()` | N → kips unit conversion |
| `scale_nm_to_kips_ft()` | N·m → kip-ft unit conversion |
| `scale_m_to_inches()` | m → in unit conversion |

---

## Design Principles

1. **Separation of concerns** – thermal and structural stacks are fully independent; each has its own FastAPI app, Bokeh viewer, SQL query module, and HTML template.
2. **No breaking changes** – existing tools in `2D-THERMAL/`, `3D-STRUCTURAL/`, and the Bokeh viewers continue to work standalone (no FastAPI required).
3. **Thin wrappers** – FastAPI apps do not duplicate Bokeh logic; they only embed the Bokeh viewer via `server_document()`.
4. **Framework-agnostic core** – `shared/database` and `shared/data` have no UI dependencies; `shared/visualization` uses only the standard library in its base class.

