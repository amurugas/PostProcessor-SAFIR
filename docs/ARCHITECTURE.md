# PostProcessor-SAFIR – Architecture Guide

## Overview

PostProcessor-SAFIR is a collection of Python tools for post-processing [SAFIR](https://www.uee.uliege.be/cms/c_4016728/en/uee-safir) finite-element analysis results.  Results are stored in SQLite databases and explored through interactive Bokeh/Streamlit dashboards, Rhino visualisers, and CSV exports.

```
PostProcessor-SAFIR/
├── shared/                  ← Reusable utilities (this PR)
│   ├── database/            ← Abstract + concrete DB managers
│   ├── utils/               ← Config, logging, validation, formatting
│   ├── visualization/       ← Base viewer, colour schemes, export
│   └── data/                ← SAFIR parsers and processing pipelines
├── 2D-THERMAL/              ← 2-D thermal analysis tools
│   ├── 2_2D-Thermal-Create-DB/
│   ├── 4_2D-Thermal-Bokeh-Dashboard/
│   └── 5_2D-Thermal-Rhino-Visualizer/
├── 3D-STRUCTURAL/           ← 3-D structural analysis tools
│   ├── 2_3D-Struct-Create-DB/
│   ├── 4_3D-Struct-Rhino-Movie/
│   ├── 5_3D-Struct-Beam-Forces-Viewer/
│   ├── 6_3D-Struct-Node-Displacement-Viewer/
│   ├── 7_3D-Struct-Beam-FiberStress/
│   ├── 8_3D-Struct-Slab-MohrStress-Plotter/
│   └── 9_3D-Struct-Slab-Stress-Plotter/
├── SAFIR-Dashboard/         ← Streamlit multi-tool dashboard
└── _Archive/                ← Legacy / reference code (not maintained)
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
        ┌────────────────────────┼──────────────────────┐
        ▼                        ▼                       ▼
  2D-THERMAL tools       3D-STRUCTURAL tools      SAFIR-Dashboard
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
            ├─ shared.data.processors.*Processor
            │         (aggregations, statistics)
            │
            └─ shared.visualization.*Viewer
                      (Bokeh / Streamlit / CSV)
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
| `format_table_row()` | Fixed-width table row for CLI output |
| `scale_n_to_kips()` | N → kips unit conversion |
| `scale_nm_to_kips_ft()` | N·m → kip-ft unit conversion |
| `scale_m_to_inches()` | m → in unit conversion |

---

## Design Principles

1. **No breaking changes** – existing tools in `2D-THERMAL/`, `3D-STRUCTURAL/`, and `SAFIR-Dashboard/` continue to work standalone.
2. **Incremental migration** – tools can import from `shared/` one module at a time.
3. **Thin wrappers** – `shared/` does not re-implement business logic; it extracts duplicated plumbing.
4. **Framework-agnostic** – `shared/database` and `shared/data` have no UI dependencies; `shared/visualization` uses only the standard library in its base class.
