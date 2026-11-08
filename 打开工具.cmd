@echo off
cd /d "%~dp0"
python "%~dp0pathnamesake.py" --gui
if errorlevel 1 pause
