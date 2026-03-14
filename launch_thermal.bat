@echo off
REM ============================================================
REM  launch_thermal.bat
REM  Launch the SAFIR 2-D Thermal Viewer as a standalone Bokeh app.
REM
REM  Thermal viewer : http://localhost:5006/thermal_viewer
REM ============================================================

cd /d "%~dp0"

REM --- (Optional) Set the default database path here ----------
REM set SAFIR_DB_PATH=C:\path\to\Raw.db

echo =======================================================
echo  SAFIR Thermal Viewer  --  Standalone
echo  URL : http://localhost:5006/thermal_viewer
echo =======================================================
echo.
echo Press Ctrl+C to stop the server.
echo.

.venv\Scripts\bokeh serve apps\thermal_viewer.py ^
    --show ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

pause
