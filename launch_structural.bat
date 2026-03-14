@echo off
REM ============================================================
REM  launch_structural.bat
REM  Launch the SAFIR 3-D Structural Viewer (full stack).
REM
REM  Bokeh structural server : http://localhost:5007/structural_viewer
REM  FastAPI structural shell : http://localhost:8001
REM
REM  This script starts both servers.
REM  Open http://localhost:8001 in your browser.
REM ============================================================

cd /d "%~dp0"

REM ── Configuration ────────────────────────────────────────────
REM Set SAFIR_CASES_DIR to the root folder that contains one
REM sub-folder per case.  Each sub-folder must have a *.db file.
SET SAFIR_CASES_DIR=C:\Users\am1\PycharmProjects\PostProcessor-SAFIR\SAFIR\Cases

REM Bokeh structural server URL (leave as-is for localhost setup)
SET BOKEH_STRUCTURAL_URL=http://localhost:5007/structural_viewer

echo =======================================================
echo  SAFIR Structural Results Viewer
echo  Bokeh server  : http://localhost:5007/structural_viewer
echo  FastAPI shell : http://localhost:8001
echo  Cases dir     : %SAFIR_CASES_DIR%
echo =======================================================
echo.
echo Starting Bokeh structural server...
echo.

REM Start Bokeh structural server in a new window
start "SAFIR Bokeh Structural" .venv\Scripts\bokeh serve ^
    apps\structural_viewer.py ^
    --port 5007 ^
    --allow-websocket-origin=* ^
    --log-level=info

REM Give Bokeh a moment to start
timeout /t 3 /nobreak >nul

echo Starting FastAPI structural server...
echo.
echo Open your browser at: http://localhost:8001
echo.

.venv\Scripts\uvicorn apps.fastapi_structural:app ^
    --host 0.0.0.0 ^
    --port 8001

pause
