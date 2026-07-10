# Robotik Atolyesi Envanter Yonetim Sistemi

Flask inventory and request tracker for a robotics workshop.

## Problem

Robotics workshops often share Arduino boards, sensors, motors, cables, and tools across many student projects. Without a simple request and approval flow, parts can be lost, over-requested, or tracked manually.

## Solution

This project provides a local web app for managing workshop inventory and student requests:

- Students can search products and add parts to a cart.
- Requests include student and project details.
- Admin users can approve or reject requests.
- Approved requests reduce stock counts.
- Inventory can be imported from Excel.
- Admin password and Flask secret key are configured through environment variables, not hard-coded credentials.

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- pandas / openpyxl for Excel import
- python-dotenv for local configuration

## Setup

Use Python 3.8 or newer.

Install dependencies:

```powershell
pip install -r requirements.txt
```

Copy the example environment file:

```powershell
copy .env.example .env
```

Edit `.env` before running:

```text
ATOLYE_SECRET_KEY=use-a-long-random-secret-key
ATOLYE_ADMIN_PASSWORD=use-a-strong-admin-password
ATOLYE_DEBUG=false
```

Generate a strong secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Prepare `inventory.xlsx` with these columns if you want to import inventory:

```text
name, description, quantity, category
```

Import Excel data:

```powershell
python import_excel.py
```

Run the app:

```powershell
python app.py
```

Open:

```text
http://localhost:5000
```

## Admin

Admin panel:

```text
http://localhost:5000/admin
```

The admin password is not stored in the repository. Set `ATOLYE_ADMIN_PASSWORD` in `.env` or system environment variables before the first run.

## Verification

- Run `python app.py` and open `http://localhost:5000`.
- Confirm products appear after the database is created or Excel import is run.
- Submit a test request from the cart flow.
- Log into `/admin` with the password from `.env`.
- Approve a request and confirm stock decreases.

## Demo / Evidence

- Demonstrates a real robotics-workshop workflow: inventory search, part request, admin approval, and stock update.
- Uses `.env.example` so default credentials are not published.
- Public roadmap is tracked in GitHub Issues.

## Security Notes

- There is no default admin password.
- Flask `SECRET_KEY` is not stored in source code.
- Keep `.env` out of Git.
- Use `ATOLYE_DEBUG=false` on shared networks or demos.

## Roadmap

- Add screenshots of the request and admin flows.
- Add basic tests for request approval and stock updates.
- Add password hashing and named admin users.
- Add a short demo GIF for the profile README.

## Status

Working local prototype for robotics workshop inventory and request tracking. The next portfolio step is to add screenshots, tests, and a small release note.
