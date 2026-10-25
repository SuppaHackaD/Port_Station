@echo off
cd /d "%~dp0\.."
python -m achievement_extractor
if errorlevel 1 pause
