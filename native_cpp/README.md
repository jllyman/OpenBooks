# OpenBooks Native C++

This is a native C++17 version of OpenBooks designed to compile locally on Windows without external runtime dependencies.

## Current shape

- Console application
- Local file-backed storage in `data/*.csv`
- Tracks customers, jobs, invoices, invoice line items, bills, and payments
- Provides dashboard-style AR/AP summary calculations

## Build

### Option 1: Visual Studio Build Tools

1. Install Visual Studio Build Tools with Desktop C++.
2. Install CMake and make sure it is in `PATH`.
3. Run `build_native.bat`

### Option 2: MinGW

1. Install MinGW-w64 and CMake.
2. Open a shell where `g++` and `cmake` are available.
3. Run `build_native.bat`

## Run

After building, run:

- `build\Release\openbooks_native.exe`, or
- `build\openbooks_native.exe`

The app creates and updates CSV files in the local `data` folder.
