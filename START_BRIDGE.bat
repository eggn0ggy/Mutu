@echo off
cd /d %~dp0app
echo Starting Mutu Stratum bridge on port 3333...
echo Point a Bitaxe at this computer's IP address, port 3333.
python stratum_bridge.py
pause
