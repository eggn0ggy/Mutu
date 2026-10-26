@echo off
cd /d %~dp0
echo WARNING: this deletes the saved testnet chain and starts again from genesis.
echo The current chain (balances, height, addresses) will be gone forever.
echo.
echo Press any key to DELETE the saved chain and start fresh, or close this window to keep it.
pause >nul
del data\chain_state.json 2>nul
cd app
python mutu_live.py
pause
