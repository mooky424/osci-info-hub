# OSCI Partner Hub

Django-based system for managing community partners, contacts, needs repository entries, socioeconomic profiles, and past interventions.

## Features

- Partner management (create, view, update, archive)
- Needs Repository management
- Past interventions management
- Socioeconomic profile tracking
- CSV bulk import (single CSV format)
- PDF export for partner details
- Authentication with custom user model

## Requirements

- Python 3.13+
- pip

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

1. Create and activate virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create environment file:

```bash
cp .env.example .env
```

4. Apply migrations:

```bash
python manage.py migrate
```

5. Create admin user (optional but recommended):

```bash
python manage.py createsuperuser
```

6. Run development server:

```bash
python manage.py runserver
```

Open:

- App: http://127.0.0.1:8000/partners/
- Login: http://127.0.0.1:8000/users/login/
- Admin: http://127.0.0.1:8000/admin/

## Environment Variables

The app reads `.env` from this directory.

If all PostgreSQL values are present, PostgreSQL is used; otherwise SQLite is used.

```env
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```
