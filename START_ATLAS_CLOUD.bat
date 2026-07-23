@echo off
setlocal EnableExtensions
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Start-AtlasCloud.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" echo Atlas Cloud ComfyUI stopped with exit code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
