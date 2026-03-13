@echo off
REM ============================================================
REM launch_bokeh.bat
REM Launch the Bokeh structural results viewer server.
REM
REM Bokeh listens on http://localhost:5006/app
REM Run this BEFORE opening launch_fastapi.bat.
REM
REM For local-network use, access via:
REM   http://<your-PC-IP>:5006/app  (standalone)
REM   http://<your-PC-IP>:8000       (via FastAPI shell)
REM ============================================================

cd /d "%~dp0"

echo =======================================================
echo  SAFIR Structural Results Viewer  --  Bokeh Server
echo  URL : http://localhost:5006/app
echo =======================================================
echo.

.venv\Scripts\bokeh serve viewer\app.py ^
    --port 5006 ^
    --allow-websocket-origin=* ^
    --log-level=info

REM NOTE: --allow-websocket-origin=* allows connections from any host.
REM       Appropriate for a dedicated local-network PC.
REM       For tighter security, replace * with the exact hostname, e.g.:
REM         --allow-websocket-origin=localhost:8000

pause
