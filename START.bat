@echo off
setlocal
cd /d "%~dp0"
if not exist "PSDBridge.exe" (
  echo PSDBridge.exe is missing. Extract the entire ZIP first.
  pause
  exit /b 1
)
start "" "%~dp0PSDBridge.exe" %*
