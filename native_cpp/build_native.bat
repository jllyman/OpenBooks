@echo off
cd /d %~dp0

where cmake >nul 2>nul
if errorlevel 1 (
    echo CMake was not found in PATH.
    echo Install Visual Studio Build Tools or MinGW plus CMake, then run this script again.
    exit /b 1
)

if not exist build (
    mkdir build
)

cmake -S . -B build
if errorlevel 1 exit /b 1

cmake --build build --config Release
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo Run build\Release\openbooks_native.exe or build\openbooks_native.exe depending on your generator.
