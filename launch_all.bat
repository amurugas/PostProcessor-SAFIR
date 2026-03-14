@echo off
REM ============================================================
REM  launch_all.bat
REM  Launch both Bokeh viewers AND the FastAPI shell together.
REM
REM  Run this script to start everything at once:
REM    Structural viewer : http://localhost:5006/structural_viewer
REM    Thermal viewer    : http://localhost:5006/thermal_viewer
REM    FastAPI shell     : http://localhost:8000
REM ============================================================

cd /d "%~dp0"

REM ── Configuration ────────────────────────────────────────────
REM Set SAFIR_CASES_DIR to the root folder that contains one
REM sub-folder per case.  Each sub-folder must have a *.db file.
SET SAFIR_CASES_DIR=%USERPROFILE%\SAFIR\Cases

REM Bokeh server URLs (leave as-is for local single-machine setup)
SET BOKEH_URL=http://localhost:5006/structural_viewer
SET BOKEH_THERMAL_URL=http://localhost:5006/thermal_viewer

echo =======================================================
echo  SAFIR Results Viewer  --  All Components
echo  Structural Bokeh : http://localhost:5006/structural_viewer
echo  Thermal Bokeh    : http://localhost:5006/thermal_viewer
echo  FastAPI shell    : http://localhost:8000
echo  Cases dir        : %SAFIR_CASES_DIR%
echo =======================================================
echo.
echo Starting Bokeh server (both viewers)...
echo.

REM Start Bokeh server in a new window
start "SAFIR Bokeh Server" .venv\Scripts\bokeh serve ^
    apps\structural_viewer.py apps\thermal_viewer.py ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

REM Give Bokeh a moment to start
timeout /t 3 /nobreak >nul

echo Starting FastAPI server...
echo.

.venv\Scripts\uvicorn apps.fastapi_shell:app ^
    --host 0.0.0.0 ^
    --port 8000

pause
