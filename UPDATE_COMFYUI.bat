@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\UPDATE_COMFYUI.log"

echo.>>"%LOG_FILE%"
echo ==== [%DATE% %TIME%] UPDATE_COMFYUI ====>>"%LOG_FILE%"
echo Updating ComfyUI from the official master/Nightly branch...

git -c "safe.directory=%~dp0ComfyUI" -C "%~dp0ComfyUI" fetch origin master >>"%LOG_FILE%" 2>&1
if errorlevel 1 goto :failed
git -c "safe.directory=%~dp0ComfyUI" -C "%~dp0ComfyUI" merge --ff-only FETCH_HEAD >>"%LOG_FILE%" 2>&1
if errorlevel 1 goto :failed

REM No --upgrade: keeps bundled PyTorch intact while satisfying pinned ComfyUI requirements.
"%~dp0python_embeded\python.exe" -m pip install -r "%~dp0ComfyUI\requirements.txt" >>"%LOG_FILE%" 2>&1
if errorlevel 1 goto :failed

REM Keep the built-in ComfyUI-Manager requirements aligned with the updated core.
if exist "%~dp0ComfyUI\manager_requirements.txt" (
    "%~dp0python_embeded\python.exe" -m pip install -r "%~dp0ComfyUI\manager_requirements.txt" >>"%LOG_FILE%" 2>&1
    if errorlevel 1 goto :failed
)

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
