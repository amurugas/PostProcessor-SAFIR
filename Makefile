# PostProcessor-SAFIR – Build & Development Automation
#
# Targets
# -------
#   make install       Install runtime dependencies
#   make dev           Install dev dependencies (includes runtime)
#   make lint          Run flake8 on the shared/ package
#   make test          Run the test suite with coverage
#   make clean         Remove Python bytecode caches

.PHONY: install dev lint test clean

PYTHON  ?= python3
PIP     ?= $(PYTHON) -m pip
FLAKE8  ?= $(PYTHON) -m flake8
PYTEST  ?= $(PYTHON) -m pytest

install:
	$(PIP) install -r requirements-base.txt

dev:
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

lint:
	$(FLAKE8) shared/ --max-line-length=100

test:
	$(PYTEST) --cov=shared --cov-report=term-missing -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
