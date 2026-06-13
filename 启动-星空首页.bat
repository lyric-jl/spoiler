@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   FitSandbox - Starfield homepage (port 8781)
echo   Starting local server, then opening page.
echo   (keep the minimized server window open)
echo ============================================
start "FitSandbox-Server" /min cmd /c "set PYTHONUTF8=1 && python -m sandbox3.server --port 8781"
timeout /t 4 >nul
start "" http://127.0.0.1:8781/landing
exit
