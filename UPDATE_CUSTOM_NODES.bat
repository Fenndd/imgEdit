@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "NODE_DIR=%~dp0ComfyUI\custom_nodes\ComfyUI-GGUF"
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\UPDATE_CUSTOM_NODES.log"

echo.>>"%LOG_FILE%"
echo ==== [%DATE% %TIME%] UPDATE_CUSTOM_NODES ====>>"%LOG_FILE%"
echo Updating ComfyUI-GGUF only...

git -c "safe.directory=%NODE_DIR%" -C "%NODE_DIR%" pull --ff-only origin main >>"%LOG_FILE%" 2>&1
if errorlevel 1 goto :failed
"%~dp0python_embeded\python.exe" -m pip install -r "%NODE_DIR%\requirements.txt" >>"%LOG_FILE%" 2>&1
if errorlevel 1 goto :failed

echo Update completed.>>"%LOG_FILE%"
echo Update completed. Full log: "%LOG_FILE%"
pause
exit /b 0

:failed
set "EXIT_CODE=%ERRORLEVEL%"
echo Update failed with exit code %EXIT_CODE%.>>"%LOG_FILE%"
echo Update failed. See "%LOG_FILE%"
pause
exit /b %EXIT_CODE%
