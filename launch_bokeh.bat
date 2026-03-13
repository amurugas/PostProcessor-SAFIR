@echo off
REM ============================================================
REM launch_bokeh.bat
REM Launch both Bokeh viewers (structural + thermal) on one server.
REM
REM Structural viewer : http://localhost:5006/app
REM Thermal viewer    : http://localhost:5006/main
REM
REM Run this BEFORE opening launch_fastapi.bat.
REM
REM For local-network use, access via:
REM   http://<your-PC-IP>:5006/app  (standalone structural)
REM   http://<your-PC-IP>:5006/main (standalone thermal)
REM   http://<your-PC-IP>:8000       (via FastAPI shell)
REM ============================================================

cd /d "%~dp0"

echo =======================================================
echo  SAFIR Results Viewer  --  Bokeh Server
echo  Structural : http://localhost:5006/app
echo  Thermal    : http://localhost:5006/main
echo =======================================================
echo.

.venv\Scripts\bokeh serve viewer\app.py bokeh_thermal\main.py ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

REM NOTE: --allow-websocket-origin=* allows connections from any host.
REM       Appropriate for a dedicated local-network PC.
REM       For tighter security, replace * with the exact hostname, e.g.:
REM         --allow-websocket-origin=localhost:8000

pause
