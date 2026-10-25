@echo off
cd /d "%~dp0"
python -m port_station gui
if errorlevel 1 pause
