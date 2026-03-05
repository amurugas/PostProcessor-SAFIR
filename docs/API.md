# PostProcessor-SAFIR – Shared API Reference

This document describes the public API exposed by the `shared/` package.

---

## shared.database

### BaseDatabaseManager

```python
class BaseDatabaseManager(db_path: str)
```

Abstract base class for all SAFIR SQLite database managers.

| Member | Signature | Description |
|---|---|---|
| `connect()` | `() → sqlite3.Connection` | Returns an open connection with FK enforcement |
| `create_tables()` | `() → None` | **Abstract.** Create the analysis-specific schema |
| `insert_timestamp(time)` | `(float) → int` | Insert a time value; return the row `id` |
| `clear_database()` | `() → None` | Prompt then wipe all rows |
| `create_views()` | `() → None` | Create convenience SQL views (override as needed) |

---

### ThermalDatabaseManager

```python
class ThermalDatabaseManager(db_path: str)
```

Extends `BaseDatabaseManager`.  Creates the 2D-thermal schema.

**Tables**

| Table | Key Columns |
|---|---|
| `timestamps` | `id`, `time` |
| `model_data` | `name`, `value`, `description` |
| `temperature_curve` | `time`, `temperature` |
| `node_coordinates` | `node_id`, `x`, `y` |
| `solid_mesh` | `solid_id`, `N1–N4`, `material_tag` |
| `material_list` | `material_tag`, `material_name` |
| `node_temperatures` | `timestamp_id`, `node_id`, `Temperature` |
| `max_temp_by_material` | `material_tag`, `timestamp_id`, `max_temp` |

---

### StructuralDatabaseManager

```python
class StructuralDatabaseManager(db_path: str)
```

Extends `BaseDatabaseManager`.  Creates the 3D-structural schema.

**Tables**

| Table | Key Columns |
|---|---|
| `timestamps` | `id`, `time` |
| `model_data` | `name`, `value`, `description` |
| `temperature_curve` | `time`, `temperature` |
| `node_coordinates` | `node_id`, `x`, `y`, `z` |
| `beam_nodes` | `beam_id`, `N1–N4`, `beam_tag` |
| `shell_nodes` | `shell_id`, `N1–N4`, `shell_tag` |
| `node_fixity` | `node_id`, `DOF1–DOF7` |
| `beam_section` | `beam_tag`, `section` |
| `shell_section` | `shell_tag`, `section` |
| `shell_loads` | `load_id`, `shell_id`, `P1–P3` |
| `material_list` | `material_tag`, `material_name` |
| `node_displacements` | `timestamp_id`, `node_id`, `D1–D7` |
| `beam_forces` | `timestamp_id`, `beam_id`, `N`, `Mz`, `My`, `Mw`, `Mr2`, `Vz`, `Vy` |
| `shell_strains` | `timestamp_id`, `shell_id`, `integration_point`, `thickness`, `Sx–Sz`, `Px–Pz`, `Dx–Dz` |
| `rebar_strains` | `timestamp_id`, `shell_id`, `nga`, `rebar_id`, `eps_sx`, `eps_sy` |
| `reactions` | `timestamp_id`, `node_id`, `R1–R7` |

**Views** (created by `create_views()`)

| View | Description |
|---|---|
| `beam_section_lookup` | Joins `beam_nodes` ↔ `beam_section` |
| `shell_section_lookup` | Joins `shell_nodes` ↔ `shell_section` |

---

## shared.data

### FireCurveParser

```python
class FireCurveParser(file_path: str)
```

| Method | Returns | Description |
|---|---|---|
| `parse()` | `list[tuple[float, float]]` | List of `(time, temperature)` pairs |

---

### XmlParser

```python
class XmlParser(xml_path: str)
```

| Method | Returns | Description |
|---|---|---|
| `parse()` | `lxml.objectify` root element | Parsed SAFIR XML result tree |

---

### TemperatureProcessor

```python
class TemperatureProcessor(db_path: str)
```

| Method | Returns | Description |
|---|---|---|
| `calc_max_temp_by_material()` | `list[dict]` | Peak temperature per material per timestep |
| `get_avg_temp_by_material()` | `dict[int, dict]` | Avg temperature time-series per material |

---

### DisplacementProcessor

```python
class DisplacementProcessor(db_path: str)
```

| Method | Returns | Description |
|---|---|---|
| `get_displacement_time_series(node_id, dof)` | `tuple[list[float], list[float]]` | `(times, displacements)` for one node/DOF |
| `get_max_displacement_per_node(dof)` | `list[dict]` | Peak `abs(displacement)` per node |

---

## shared.visualization

### BaseViewer

```python
class BaseViewer(db_path: str, title: str = "SAFIR Results Viewer")
```

| Member | Description |
|---|---|
| `build_layout()` | **Abstract.** Construct the UI layout |
| `show()` | **Abstract.** Render / serve the viewer |
| `_run_query(query, params)` | Execute a SELECT against `db_path` |
| `get_all_timestamps()` | `list[float]` – all simulation times |
| `get_fire_curve()` | `(times, temps)` from `temperature_curve` |

---

### Color Palettes

| Symbol | Type | Description |
|---|---|---|
| `MATERIAL_COLORS` | `list[str]` | 10 hex colours, cyclic by material index |
| `TEMPERATURE_PALETTE` | `list[str]` | 11-stop blue→red diverging palette |
| `DEFAULT_LINE_COLORS` | `list[str]` | 8 named colours for sequential series |
| `get_material_color(index)` | `str` | Cyclic lookup into `MATERIAL_COLORS` |

---

### Export Utilities

| Function | Signature | Description |
|---|---|---|
| `export_to_csv(df, output_path, index)` | `str` | Write DataFrame to CSV; return abs path |
| `export_to_excel(df, output_path, sheet_name, index)` | `str` | Write DataFrame to xlsx; return abs path |
| `ensure_output_dir(base_dir, sub)` | `str` | Create and return `base_dir/sub` |

---

## shared.utils

### Config

```python
@dataclass
class Config
```

| Attribute | Env var | Default |
|---|---|---|
| `log_level` | `LOG_LEVEL` | `"INFO"` |
| `log_format` | `LOG_FORMAT` | `"%(asctime)s - …"` |
| `db_dir` | `DB_DIR` | `"."` |
| `data_dir` | `DATA_DIR` | `"data"` |
| `output_dir` | `OUTPUT_DIR` | `"output"` |
| `default_analysis_type` | `DEFAULT_ANALYSIS_TYPE` | `"structural"` |

---

### setup_logger

```python
def setup_logger(name: str, level: str | None = None, fmt: str | None = None) → logging.Logger
```

Returns a configured logger.  Reads `LOG_LEVEL` / `LOG_FORMAT` from the environment when arguments are omitted.

---

### Validators

| Function | Raises | Description |
|---|---|---|
| `validate_file_exists(path, label)` | `ValueError` | Path must be an existing file |
| `validate_db_path(path)` | `ValueError` | Parent directory must exist |
| `validate_xml_path(path)` | `ValueError` | Must be an existing `.xml` file |

---

### Formatters

| Function | Description |
|---|---|
| `format_value(value, decimals, unit)` | Numeric string with optional unit |
| `format_table_row(values, width)` | Fixed-width `\|`-delimited row |
| `scale_n_to_kips(value)` | N → kips |
| `scale_nm_to_kips_ft(value)` | N·m → kip-ft |
| `scale_m_to_inches(value)` | m → inches |
