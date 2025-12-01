@echo off
REM TNI Seed Harvester - Process Harvest Data
REM Double-click this file after a harvest run to process the data

cd /d "%~dp0"
echo.
echo ========================================
echo TNI Seed Harvester - Processing Data
echo ========================================
echo.

python process-harvest.py %*

echo.
pause
