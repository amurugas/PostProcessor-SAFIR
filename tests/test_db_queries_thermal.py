"""
tests/test_db_queries_thermal.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for db_queries_thermal.py.

Uses an in-memory SQLite database that mirrors the 2-D thermal schema.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pandas as pd
import pytest

import db_queries_thermal as dbq


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def thermal_db(tmp_path):
    """Create a minimal thermal SQLite database for testing."""
    db_file = str(tmp_path / "thermal_test.db")
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        CREATE TABLE timestamps (
            id   INTEGER PRIMARY KEY,
            time REAL NOT NULL
        );
        CREATE TABLE node_coordinates (
            id      INTEGER PRIMARY KEY,
            node_id INTEGER NOT NULL,
            x       REAL NOT NULL,
            y       REAL NOT NULL
        );
        CREATE TABLE node_temperatures (
            id           INTEGER PRIMARY KEY,
            timestamp_id INTEGER NOT NULL,
            node_id      INTEGER NOT NULL,
            Temperature  REAL NOT NULL
        );

        INSERT INTO timestamps VALUES (1, 0.0), (2, 10.0), (3, 20.0);
        INSERT INTO node_coordinates VALUES
            (1, 1, 0.0, 0.0),
            (2, 2, 1.0, 0.0),
            (3, 3, 0.5, 1.0);
        INSERT INTO node_temperatures VALUES
            (1, 1, 1,  20.0), (2, 1, 2,  25.0), (3, 1, 3,  22.0),
            (4, 2, 1, 100.0), (5, 2, 2, 150.0), (6, 2, 3, 120.0),
            (7, 3, 1, 300.0), (8, 3, 2, 400.0), (9, 3, 3, 350.0);
        """
    )
    conn.close()
    return db_file


@pytest.fixture()
def empty_db(tmp_path):
    """SQLite database with no tables."""
    db_file = str(tmp_path / "empty.db")
    conn = sqlite3.connect(db_file)
    conn.close()
    return db_file


# ---------------------------------------------------------------------------
# Tests for existing helpers
# ---------------------------------------------------------------------------


class TestGetThermalSections:
    def test_returns_section_1_when_data_exists(self, thermal_db):
        df = dbq.get_thermal_sections(thermal_db)
        assert list(df.columns) == ["section_id"]
        assert len(df) == 1
        assert df.iloc[0]["section_id"] == 1

    def test_returns_empty_for_empty_db(self, empty_db):
        df = dbq.get_thermal_sections(empty_db)
        assert df.empty
        assert "section_id" in df.columns


class TestGetThermalTimesteps:
    def test_returns_all_timesteps(self, thermal_db):
        df = dbq.get_thermal_timesteps(thermal_db)
        assert list(df.columns) == ["id", "time"]
        assert len(df) == 3
        assert list(df["time"]) == [0.0, 10.0, 20.0]

    def test_returns_empty_for_empty_db(self, empty_db):
        df = dbq.get_thermal_timesteps(empty_db)
        assert df.empty
        assert set(df.columns) == {"id", "time"}


# ---------------------------------------------------------------------------
# Tests for get_temperature_grid
# ---------------------------------------------------------------------------


class TestGetTemperatureGrid:
    def test_returns_correct_columns(self, thermal_db):
        df = dbq.get_temperature_grid(thermal_db, section_id=1, timestep_id=1)
        assert set(df.columns) == {"node_id", "x", "y", "temperature"}

    def test_returns_all_nodes_for_timestep(self, thermal_db):
        df = dbq.get_temperature_grid(thermal_db, section_id=1, timestep_id=1)
        assert len(df) == 3
        assert set(df["node_id"].tolist()) == {1, 2, 3}

    def test_correct_temperatures_at_timestep_2(self, thermal_db):
        df = dbq.get_temperature_grid(thermal_db, section_id=1, timestep_id=2)
        df = df.set_index("node_id")
        assert df.loc[1, "temperature"] == pytest.approx(100.0)
        assert df.loc[2, "temperature"] == pytest.approx(150.0)
        assert df.loc[3, "temperature"] == pytest.approx(120.0)

    def test_correct_coordinates(self, thermal_db):
        df = dbq.get_temperature_grid(thermal_db, section_id=1, timestep_id=1)
        df = df.set_index("node_id")
        assert df.loc[1, "x"] == pytest.approx(0.0)
        assert df.loc[1, "y"] == pytest.approx(0.0)
        assert df.loc[2, "x"] == pytest.approx(1.0)
        assert df.loc[3, "y"] == pytest.approx(1.0)

    def test_ordered_by_node_id(self, thermal_db):
        df = dbq.get_temperature_grid(thermal_db, section_id=1, timestep_id=1)
        assert df["node_id"].tolist() == sorted(df["node_id"].tolist())

    def test_section_id_ignored_single_section(self, thermal_db):
        """section_id is unused in the schema; any value should return same data."""
        df1 = dbq.get_temperature_grid(thermal_db, section_id=1, timestep_id=1)
        df2 = dbq.get_temperature_grid(thermal_db, section_id=99, timestep_id=1)
        pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))

    def test_returns_empty_for_empty_db(self, empty_db):
        df = dbq.get_temperature_grid(empty_db, section_id=1, timestep_id=1)
        assert df.empty
        assert set(df.columns) == {"node_id", "x", "y", "temperature"}

    def test_missing_node_temperatures_table(self, tmp_path):
        """Only node_coordinates exists – should return empty DataFrame."""
        db_file = str(tmp_path / "partial.db")
        conn = sqlite3.connect(db_file)
        conn.execute(
            "CREATE TABLE node_coordinates (id INTEGER PRIMARY KEY, node_id INTEGER, x REAL, y REAL)"
        )
        conn.execute("INSERT INTO node_coordinates VALUES (1, 1, 0.0, 0.0)")
        conn.close()

        df = dbq.get_temperature_grid(db_file, section_id=1, timestep_id=1)
        assert df.empty
        assert set(df.columns) == {"node_id", "x", "y", "temperature"}


# ---------------------------------------------------------------------------
# Tests for get_temperature_history
# ---------------------------------------------------------------------------


class TestGetTemperatureHistory:
    def test_returns_correct_columns(self, thermal_db):
        df = dbq.get_temperature_history(thermal_db, section_id=1, node_id=1)
        assert set(df.columns) == {"time", "temperature"}

    def test_returns_all_timesteps_for_node(self, thermal_db):
        df = dbq.get_temperature_history(thermal_db, section_id=1, node_id=1)
        assert len(df) == 3
        assert list(df["time"]) == [0.0, 10.0, 20.0]

    def test_correct_temperatures_for_node_1(self, thermal_db):
        df = dbq.get_temperature_history(thermal_db, section_id=1, node_id=1)
        assert list(df["temperature"]) == pytest.approx([20.0, 100.0, 300.0])

    def test_correct_temperatures_for_node_2(self, thermal_db):
        df = dbq.get_temperature_history(thermal_db, section_id=1, node_id=2)
        assert list(df["temperature"]) == pytest.approx([25.0, 150.0, 400.0])

    def test_ordered_by_time(self, thermal_db):
        df = dbq.get_temperature_history(thermal_db, section_id=1, node_id=3)
        assert df["time"].tolist() == sorted(df["time"].tolist())

    def test_section_id_ignored_single_section(self, thermal_db):
        """section_id is unused in the schema; any value should return same data."""
        df1 = dbq.get_temperature_history(thermal_db, section_id=1, node_id=1)
        df2 = dbq.get_temperature_history(thermal_db, section_id=42, node_id=1)
        pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))

    def test_returns_empty_for_empty_db(self, empty_db):
        df = dbq.get_temperature_history(empty_db, section_id=1, node_id=1)
        assert df.empty
        assert set(df.columns) == {"time", "temperature"}

    def test_missing_timestamps_table(self, tmp_path):
        """Only node_temperatures exists – should return empty DataFrame."""
        db_file = str(tmp_path / "partial.db")
        conn = sqlite3.connect(db_file)
        conn.execute(
            "CREATE TABLE node_temperatures "
            "(id INTEGER PRIMARY KEY, timestamp_id INTEGER, node_id INTEGER, Temperature REAL)"
        )
        conn.execute("INSERT INTO node_temperatures VALUES (1, 1, 1, 100.0)")
        conn.close()

        df = dbq.get_temperature_history(db_file, section_id=1, node_id=1)
        assert df.empty
        assert set(df.columns) == {"time", "temperature"}
