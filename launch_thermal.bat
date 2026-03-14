@echo off
REM ============================================================
REM  launch_thermal.bat
REM  Launch the SAFIR 2-D Thermal Viewer (full stack).
REM
REM  Bokeh thermal server : http://localhost:5006/thermal_viewer
REM  FastAPI thermal shell : http://localhost:8000
REM
REM  This script starts both servers.
REM  Open http://localhost:8000 in your browser.
REM ============================================================

cd /d "%~dp0"

REM ── Configuration ────────────────────────────────────────────
REM Set SAFIR_CASES_DIR to the root folder that contains one
REM sub-folder per case.  Each sub-folder must have a *.db file.
SET SAFIR_CASES_DIR=%USERPROFILE%\SAFIR\Cases

REM Bokeh thermal server URL (leave as-is for localhost setup)
SET BOKEH_THERMAL_URL=http://localhost:5006/thermal_viewer

echo =======================================================
echo  SAFIR Thermal Results Viewer
echo  Bokeh server  : http://localhost:5006/thermal_viewer
echo  FastAPI shell : http://localhost:8000
echo  Cases dir     : %SAFIR_CASES_DIR%
echo =======================================================
echo.
echo Starting Bokeh thermal server...
echo.

REM Start Bokeh thermal server in a new window
start "SAFIR Bokeh Thermal" .venv\Scripts\bokeh serve ^
    apps\thermal_viewer.py ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

REM Give Bokeh a moment to start
timeout /t 3 /nobreak >nul

echo Starting FastAPI thermal server...
echo.
echo Open your browser at: http://localhost:8000
echo.

.venv\Scripts\uvicorn apps.fastapi_thermal:app ^
    --host 0.0.0.0 ^
    --port 8000

pause
