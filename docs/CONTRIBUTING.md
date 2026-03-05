# Contributing to PostProcessor-SAFIR

Thank you for your interest in contributing!  This document explains how to set up a development environment, the conventions used in the project, and the workflow for submitting changes.

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.10 |
| pip | latest |
| git | any recent version |

---

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/amurugas/PostProcessor-SAFIR.git
cd PostProcessor-SAFIR

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install shared dependencies
pip install -r requirements-base.txt

# 4. Install dev dependencies (linting, testing)
pip install -r requirements-dev.txt

# 5. Verify the installation
python -c "from shared import database, utils, visualization, data; print('OK')"
```

---

## Project Layout

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full module map.  The key rule is:

> All reusable logic goes into `shared/`.  Tool-specific scripts in `2D-THERMAL/`, `3D-STRUCTURAL/`, and `SAFIR-Dashboard/` import from `shared/` rather than duplicating code.

---

## Coding Standards

- **Python style**: [PEP 8](https://peps.python.org/pep-0008/).  Use `flake8` (bundled in `requirements-dev.txt`) for linting.
- **Type hints**: Add type annotations to all public functions and class attributes.
- **Docstrings**: Follow [NumPy docstring style](https://numpydoc.readthedocs.io/en/latest/format.html).
- **Logging**: Use `shared.utils.logger.setup_logger(__name__)` instead of `logging.basicConfig`.
- **No print statements** in library code – use `logger.info` / `logger.debug`.

---

## Adding a New Shared Module

1. Create your file under the appropriate `shared/<sub-package>/` directory.
2. Add the public symbols to that sub-package's `__init__.py`.
3. Write a brief docstring at the top of the file (purpose, parameters, example).
4. Import and re-export from `shared/__init__.py` if the symbol is truly top-level.

---

## Adding Support for a New Analysis Type

1. Create `shared/database/<type>_db.py` subclassing `BaseDatabaseManager`.
2. Create `shared/data/parsers_<type>.py` if the file format differs.
3. Create `shared/data/processors_<type>.py` for analysis-specific aggregations.
4. Document the new tables / columns in [API.md](API.md).

---

## Running the Linter

```bash
flake8 shared/
```

---

## Submitting Changes

1. Fork the repository and create a feature branch: `git checkout -b feature/my-change`.
2. Make your changes following the standards above.
3. Ensure `flake8 shared/` reports no errors.
4. Open a pull request against `main` with a clear description of the change and why it is needed.

---

## Code of Conduct

Be respectful, constructive, and patient.  All contributors are expected to follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
