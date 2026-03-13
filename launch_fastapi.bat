@echo off
REM ============================================================
REM launch_fastapi.bat
REM Launch the FastAPI web shell for the SAFIR Viewer.
REM
REM FastAPI listens on http://localhost:8000
REM The Bokeh server must already be running on port 5006.
REM ============================================================

cd /d "%~dp0"

REM ── Configuration ────────────────────────────────────────────
REM Set SAFIR_CASES_DIR to the root folder that contains one
REM sub-folder per case.  Each sub-folder must have a *.db file.
SET SAFIR_CASES_DIR=%USERPROFILE%\SAFIR\Cases

REM Bokeh server URLs (leave as-is for local single-machine setup)
SET BOKEH_URL=http://localhost:5006/app
SET BOKEH_THERMAL_URL=http://localhost:5006/main

echo =======================================================
echo  SAFIR Results Viewer  --  FastAPI Server
echo  URL              : http://localhost:8000
echo  Cases dir        : %SAFIR_CASES_DIR%
echo  Structural Bokeh : %BOKEH_URL%
echo  Thermal Bokeh    : %BOKEH_THERMAL_URL%
echo =======================================================
echo.
echo Make sure launch_bokeh.bat is already running.
echo.

.venv\Scripts\uvicorn fastapi_app:app ^
    --host 0.0.0.0 ^
    --port 8000

pause
