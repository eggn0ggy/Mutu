@echo off
cd /d "%~dp0"
echo ============================================
echo   MUTU TESTNET - SEND COINS
echo   Works whether or not START_LIVE is running:
echo   stopped = applied instantly; running = queued in the mempool
echo   and settled by the live chain on its next window.
echo ============================================
python -c "import cryptography" 2>nul || python -m pip install cryptography
python app\mutu_send.py
pause
