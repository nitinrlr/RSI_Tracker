@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows-task.ps1" %*
exit /b %ERRORLEVEL%
