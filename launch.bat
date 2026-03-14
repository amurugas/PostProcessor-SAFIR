@echo off
REM ============================================================
REM  SAFIR Results Viewer – Windows Launch Script
REM ============================================================
REM
REM  Usage:
REM    1. Double-click this file, OR
REM    2. Open a Command Prompt in this folder and run:
REM         launch.bat
REM
REM  To specify a database path, either:
REM    a) Set the environment variable before running:
REM         set SAFIR_DB_PATH=C:\path\to\Raw.db
REM         launch.bat
REM    b) Edit the DB_PATH line below.
REM
REM  The app will be accessible from other machines on the local
REM  network at http://<this-PC-hostname>:5006/structural_viewer
REM                                           or /thermal_viewer
REM ============================================================

REM --- (Optional) Set the default database path here ----------
set SAFIR_DB_PATH=C:\Users\am1\PycharmProjects\PostProcessor-SAFIR\3D-STRUCTURAL\3_3D-Struct-DB\new5.db

REM --- Launch Bokeh server with both viewers -------------------
echo Starting SAFIR Results Viewer...
echo.
echo Access the viewers at:
echo   http://localhost:5006/structural_viewer   (structural – this machine)
echo   http://localhost:5006/thermal_viewer      (thermal    – this machine)
echo   http://<your-PC-IP>:5006/structural_viewer (structural – other machines)
echo   http://<your-PC-IP>:5006/thermal_viewer    (thermal    – other machines)
echo.
echo Press Ctrl+C to stop the server.
echo.

bokeh serve apps\structural_viewer.py apps\thermal_viewer.py ^
    --show ^
    --port 5006 ^
    --allow-websocket-origin=*

REM NOTE: --allow-websocket-origin=* allows connections from any host on the
REM       network. This is appropriate for a dedicated local-network PC.
REM       For tighter security, replace * with the exact hostname or IP, e.g.:
REM         --allow-websocket-origin=192.168.1.100:5006

pause

