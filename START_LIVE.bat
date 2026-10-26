@echo off
cd /d %~dp0app
echo Starting Mutu testnet LIVE mode...
echo When it starts, open the "output" folder and double-click explorer.html.
python mutu_live.py
pause
