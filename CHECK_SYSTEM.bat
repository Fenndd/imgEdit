@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
echo === NVIDIA GPU ===
nvidia-smi
echo.
echo === ComfyUI and embedded Python ===
"%~dp0python_embeded\python.exe" --version
"%~dp0python_embeded\python.exe" -m pip show torch gguf comfyui-workflow-templates comfy-kitchen comfyui_manager | findstr /R /C:"^Name:" /C:"^Version:"
echo ComfyUI commit:
git -c "safe.directory=%~dp0ComfyUI" -C "%~dp0ComfyUI" rev-parse --short HEAD
echo ComfyUI-GGUF commit:
git -c "safe.directory=%~dp0ComfyUI\custom_nodes\ComfyUI-GGUF" -C "%~dp0ComfyUI\custom_nodes\ComfyUI-GGUF" rev-parse --short HEAD
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK_SYSTEM.ps1"
echo.
pause
