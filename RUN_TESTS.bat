@echo off
cd /d "%~dp0"
echo ============================================
echo   MUTU TESTNET - ADVERSARIAL TEST PACK
echo   Tries to rob, corrupt, and outsmart a
echo   scratch copy of the testnet. The saved
echo   chain is never touched.
echo ============================================
python -c "import cryptography" 2>nul || python -m pip install cryptography
python app\mutu_tests.py
echo.
echo Full report: output\test_report.txt
pause
