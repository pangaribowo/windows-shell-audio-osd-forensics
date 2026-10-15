@echo off
title Windows Audio & Shell OSD Agent Runtime (Port 8088)
cd /d "%~dp0\.."
echo ========================================================
echo  Windows Shell Audio OSD Agent Runtime - Port 8088
echo ========================================================
python -m scripts.main serve --port 8088
pause
