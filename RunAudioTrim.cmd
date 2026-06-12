@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RunAudioTrim.ps1" %*

if errorlevel 1 (
    echo.
    echo AudioTrim launcher exited with an error.
    pause
)
