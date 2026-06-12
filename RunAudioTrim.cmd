@echo off
setlocal

cd /d "%~dp0"
python "%~dp0audio_trim.py" --gui

if errorlevel 1 (
    echo.
    echo AudioTrim exited with an error.
    pause
)
