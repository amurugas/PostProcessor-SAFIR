@echo off
REM ============================================================
REM  launch_structural.bat
REM  Launch the SAFIR Structural Viewer as a standalone Bokeh app.
REM
REM  Structural viewer : http://localhost:5006/structural_viewer
REM ============================================================

cd /d "%~dp0"

REM --- (Optional) Set the default database path here ----------
REM set SAFIR_DB_PATH=C:\path\to\Raw.db

echo =======================================================
echo  SAFIR Structural Viewer  --  Standalone
echo  URL : http://localhost:5006/structural_viewer
echo =======================================================
echo.
echo Press Ctrl+C to stop the server.
echo.

.venv\Scripts\bokeh serve apps\structural_viewer.py ^
    --show ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

pause
