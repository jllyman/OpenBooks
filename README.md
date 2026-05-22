# OpenBooks

OpenBooks is a local-first Windows accounting and job tracking app for a fabrication and woodworking business. It runs entirely on your machine using Flask and SQLite.

There is also a native C++ version in [`native_cpp`](./native_cpp) for a compiled local workflow.

## Features

- Dashboard with AR, AP, invoice, bill, and active job totals
- Customer management
- Job tracking with due dates, status, estimates, and actual costs
- Invoicing with line items
- Vendor bills for accounts payable
- Payment tracking for money received and money paid

## Quick start

1. Open PowerShell in this folder.
2. Run `.\start_openbooks.bat`
3. Open `http://127.0.0.1:5000`

## Data

- The SQLite database is created automatically as `openbooks.db`.
- This is an MVP foundation, so it is intended to be extended with estimates, inventory, reports, tax handling, and double-entry bookkeeping later.

## Native C++ Version

- Source: `native_cpp`
- Storage: local CSV files in `native_cpp\data`
- Build helper: `native_cpp\build_native.bat`
