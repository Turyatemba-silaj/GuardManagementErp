# Security Company Management System

A Django-based management system for a security company, built from the supplied ERD. It covers Operations, Human Resource, and Finance workflows with relational models, Django admin management screens, a dashboard, and initial automated tests.

## Main Modules

- Operations: clients, sites, shifts, deployments, incidents, patrol logs, and assets.
- Human Resource: employees, roles, positions, guards, supervisors, training, attendance, leave, disciplinary actions, performance evaluations, and employee documents.
- Finance: salaries, salary advances, invoices, payments, budgets, and expenses.
- Guard Scheduling: select a site and date on the attendance page to generate scheduled guard rows from active deployments, then mark attendance.
- Responsive Management Pages: each major module has list, add, edit, and delete pages under `/records/<module>/`.

## Requirements

- Python 3.14+
- Django 6.0.5
- SQLite for local development, configurable in `security_management/settings.py`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Setup

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open the system at:

- Dashboard: http://127.0.0.1:8000/
- Guard attendance roster: http://127.0.0.1:8000/attendances/
- Example module page: http://127.0.0.1:8000/records/sites/
- Admin: http://127.0.0.1:8000/admin/

## Verification

Run Django checks and tests:

```bash
python manage.py check
python manage.py test
```

## Notes

- Uploaded patrol photos and employee documents are stored under `media/` during development.
- Salary net pay, invoice balance, paid invoice status, and budget remaining balance are calculated automatically on save.
- `TIME_ZONE` is set to `Africa/Kampala`.
