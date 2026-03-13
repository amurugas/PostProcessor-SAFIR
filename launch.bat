@echo off
REM ============================================================
REM  SAFIR Structural Results Viewer – Windows Launch Script
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
REM  network at http://<this-PC-hostname>:5006/app
REM ============================================================

REM --- (Optional) Set the default database path here ----------
REM set SAFIR_DB_PATH=C:\path\to\Raw.db

REM --- Launch Bokeh server -------------------------------------
echo Starting SAFIR Structural Viewer...
echo.
echo Access the viewer at:
echo   http://localhost:5006/app          (this machine)
echo   http://<your-PC-IP>:5006/app       (other machines on the network)
echo.
echo Press Ctrl+C to stop the server.
echo.

bokeh serve viewer\app.py ^
    --show ^
    --port 5006 ^
    --allow-websocket-origin=*

pause
