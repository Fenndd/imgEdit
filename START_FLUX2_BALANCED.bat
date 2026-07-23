@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\START_FLUX2_BALANCED.log"

echo.>>"%LOG_FILE%"
echo ==== [%DATE% %TIME%] START_FLUX2_BALANCED ====>>"%LOG_FILE%"
echo Starting local ComfyUI. Browser will open at http://127.0.0.1:8188
echo Full log: "%LOG_FILE%"

"%~dp0python_embeded\python.exe" "%~dp0ComfyUI\main.py" ^
  --windows-standalone-build ^
  --auto-launch ^
  --enable-manager ^
  --disable-api-nodes ^
  --enable-dynamic-vram ^
  --reserve-vram 1.0 ^
  --fast-disk ^
  --cache-none ^
  --preview-method auto ^
  --log-stdout >>"%LOG_FILE%" 2>&1

set "EXIT_CODE=%ERRORLEVEL%"
echo ==== [%DATE% %TIME%] ComfyUI stopped, exit code %EXIT_CODE% ====>>"%LOG_FILE%"
echo.
echo ComfyUI stopped with exit code %EXIT_CODE%.
echo See "%LOG_FILE%" for the full log.
pause
exit /b %EXIT_CODE%
