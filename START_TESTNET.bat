@echo off
cd /d %~dp0app
echo Setting up Mutu testnet (first run only, needs internet)...
python -c "import cryptography" 2>nul || python -m pip install cryptography
echo.
echo ================= STARTING MUTU TESTNET =================
python mutu_testnet.py
echo.
pause
