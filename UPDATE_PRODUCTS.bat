@echo off
cd /d "%~dp0"
echo Building latest product catalogue...
py -3 tools\build_data.py
if errorlevel 1 (
  echo.
  echo Build failed. Check the error above.
  pause
  exit /b 1
)
echo.
echo Done. Upload data\catalogue.json, data\details.json and data\build-report.json to GitHub.
pause
