@echo off
cd /d "%~dp0"
if exist "runtime\pythonw.exe" (
 "runtime\python.exe" "main.py"
) else (
 python main.py
)
