@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python build_exe.py
echo.
echo Portable app: dist\TimeTrack.exe
pause
