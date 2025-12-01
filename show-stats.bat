@echo off
REM TNI Seed Harvester - Show Database Statistics
REM Double-click to see current coverage stats

cd /d "%~dp0"
python process-harvest.py --stats
pause
