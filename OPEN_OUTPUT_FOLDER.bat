@echo off
setlocal EnableExtensions
if not exist "%~dp0ComfyUI\output" mkdir "%~dp0ComfyUI\output"
start "ComfyUI output" "%~dp0ComfyUI\output"
