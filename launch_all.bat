@echo off
REM ============================================================
REM  launch_all.bat
REM  Launch ALL viewers at once – both Bokeh servers and both
REM  FastAPI shells.
REM
REM  Thermal   Bokeh  : http://localhost:5006/thermal_viewer
REM  Structural Bokeh : http://localhost:5007/structural_viewer
REM  Thermal   FastAPI: http://localhost:8000
REM  Structural FastAPI: http://localhost:8001
REM ============================================================

cd /d "%~dp0"

REM ── Configuration ────────────────────────────────────────────
REM Set SAFIR_CASES_DIR to the root folder that contains one
REM sub-folder per case.  Each sub-folder must have a *.db file.
SET SAFIR_CASES_DIR=%USERPROFILE%\SAFIR\Cases

REM Bokeh server URLs (leave as-is for local single-machine setup)
SET BOKEH_THERMAL_URL=http://localhost:5006/thermal_viewer
SET BOKEH_STRUCTURAL_URL=http://localhost:5007/structural_viewer

echo =======================================================
echo  SAFIR Results Viewer  --  All Components
echo.
echo  Thermal   Bokeh  : http://localhost:5006/thermal_viewer
echo  Structural Bokeh : http://localhost:5007/structural_viewer
echo  Thermal   FastAPI: http://localhost:8000
echo  Structural FastAPI: http://localhost:8001
echo  Cases dir        : %SAFIR_CASES_DIR%
echo =======================================================
echo.
echo Starting Bokeh thermal server...

REM Start Bokeh thermal server in a new window
start "SAFIR Bokeh Thermal" .venv\Scripts\bokeh serve ^
    apps\thermal_viewer.py ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

echo Starting Bokeh structural server...

REM Start Bokeh structural server in a new window
start "SAFIR Bokeh Structural" .venv\Scripts\bokeh serve ^
    apps\structural_viewer.py ^
    --port 5007 ^
    --allow-websocket-origin=* ^
    --log-level=info

REM Give Bokeh servers a moment to start
timeout /t 6 /nobreak >nul

echo Starting FastAPI structural server (port 8001)...

REM Start FastAPI structural in a new window
start "SAFIR FastAPI Structural" .venv\Scripts\uvicorn apps.fastapi_structural:app ^
    --host 0.0.0.0 ^
    --port 8001

echo Starting FastAPI thermal server (port 8000)...
echo.
echo Open your browser:
echo   Thermal viewer    -^> http://localhost:8000
echo   Structural viewer -^> http://localhost:8001
echo.

.venv\Scripts\uvicorn apps.fastapi_thermal:app ^
    --host 0.0.0.0 ^
    --port 8000

pause
