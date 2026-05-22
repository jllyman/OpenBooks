@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64
if errorlevel 1 (
    echo Failed to load Visual Studio Build Tools environment.
    exit /b 1
)
cd /d "%~dp0.."
cmd
