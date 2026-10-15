@echo off
title Windows Shell DirectUI / SndVolSSO OSD Forensics Triage
cd /d "%~dp0\.."
echo ========================================================
echo  Running Windows Shell DirectUI / SndVolSSO OSD Triage
echo ========================================================
python scripts/triage_sndvol.py
echo.
echo Remediation option: to trigger automated shell re-binding:
echo python -m scripts.main sync-osd --restart-explorer
echo.
pause
