# OpenBooks Progress

## Date

- May 15, 2026

## What We Built

### Python MVP

A working local-first Windows app was created in the `OpenBooks` folder using:

- Flask
- SQLAlchemy
- SQLite

Current Python app features:

- Dashboard
- Customers
- Jobs
- Invoices
- Bills
- Payments

Important files:

- [`run.py`](./run.py)
- [`start_openbooks.bat`](./start_openbooks.bat)
- [`app/__init__.py`](./app/__init__.py)
- [`app/database.py`](./app/database.py)
- [`app/routes.py`](./app/routes.py)
- [`app/templates`](./app/templates)
- [`app/static/styles.css`](./app/static/styles.css)

Data storage for the Python version:

- SQLite database file: `openbooks.db`

Status:

- The Flask app was started successfully
- HTTP check returned `200`
- The app is currently working locally

## Native C++ Version

A native C++17 version was scaffolded in:

- [`native_cpp`](./native_cpp)

Current native C++ app shape:

- Console application
- Local CSV-backed storage
- Tracks customers, jobs, invoices, invoice items, bills, and payments
- Includes dashboard AR/AP summary calculations

Important files:

- [`native_cpp/CMakeLists.txt`](./native_cpp/CMakeLists.txt)
- [`native_cpp/build_native.bat`](./native_cpp/build_native.bat)
- [`native_cpp/src/main.cpp`](./native_cpp/src/main.cpp)
- [`native_cpp/src/models.h`](./native_cpp/src/models.h)
- [`native_cpp/src/storage.h`](./native_cpp/src/storage.h)
- [`native_cpp/src/storage.cpp`](./native_cpp/src/storage.cpp)
- [`native_cpp/README.md`](./native_cpp/README.md)

Data storage for the C++ version:

- CSV files in `native_cpp/data`

## Tooling Status

### Confirmed installed

- Python 3.14.3
- `pip`
- CMake 4.3.2

### Not yet confirmed installed

- Visual Studio Build Tools / MSVC compiler
- `cl`
- `g++`

At the time of the last build attempt, the machine did not yet have a visible C++ compiler in `PATH`.

## Last Known Build State

The C++ project could not yet be compiled because the compiler toolchain was not available in `PATH`.

The intended next checks are:

```powershell
cl
g++ --version
```

If `cl` is not available in regular PowerShell after install, use:

- `x64 Native Tools Command Prompt for VS 2022`

Then build from:

```powershell
cd C:\Users\justi\Documents\OpenBooks\native_cpp
.\build_native.bat
```

## Recommended Next Steps

1. Install Visual Studio Build Tools with `Desktop development with C++`.
2. Confirm `cl` works.
3. Build the native C++ project with `.\build_native.bat`.
4. If the build succeeds, run the generated `openbooks_native.exe`.
5. Decide whether to continue with:
   - the working Python app,
   - the native C++ console app, or
   - a future native C++ GUI version.

## Notes

- The Python version is the only version confirmed working end-to-end right now.
- The C++ version is scaffolded and ready for compilation once the compiler is installed.
- The long-term best native desktop direction would likely be a GUI app, but the current C++ version was intentionally kept dependency-light so it can compile more easily.
