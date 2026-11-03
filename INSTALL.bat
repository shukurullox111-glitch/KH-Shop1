@echo off
cd /d "%~dp0"
py -m venv .venv
if errorlevel 1 (echo Python topilmadi. Python 3.11+ o'rnating.& pause & exit /b 1)
.venv\Scripts\python.exe -m pip install -r requirements.txt
pause
