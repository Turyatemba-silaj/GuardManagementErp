# Security Standardization Guide

## Immediate Vulnerabilities Found

- `SECRET_KEY`, `DEBUG=True`, and host policy were hard-coded in `security_management/settings.py`.
- `db.sqlite3`, `media/`, and Python bytecode were present in the working tree and should not be committed.
- Uploads accepted arbitrary file extensions through generic model forms and Excel import views.
- The attendance device API is intentionally unauthenticated by user session, so it must be treated as a token-authenticated machine endpoint with strict payload limits.
- Production cookie, HTTPS, HSTS, content sniffing, and frame protection settings were not standardized.

## Implemented Baseline

- Django settings now read secrets, debug mode, hosts, CSRF origins, database settings, upload limits, and attendance API body limits from environment variables.
- Production mode requires `DJANGO_SECRET_KEY`, refuses the development fallback key, and enables secure cookies, HSTS, SSL redirect, strict referrer policy, frame denial, and content-type sniffing protection.
- Runtime artifacts and sensitive local files are ignored in `.gitignore`.
- A `.env.example` file documents the expected configuration knobs.
- Shared upload validation limits model-form uploads to approved image/document extensions, size limits, and common file signatures.
- Excel imports now validate file extension and size before parsing with `openpyxl`.
- The attendance swipe endpoint now rejects oversized JSON bodies and does not query device credentials unless both token and device ID are present.
- The public health check returns only a minimal status. Detailed environment and database diagnostics require staff access or `DJANGO_HEALTHCHECK_TOKEN`.
- `ERP_PERMANENT_LOGIN` is blocked in production unless an explicit insecure override is set for emergency-only use.
- The environment-superuser authentication shortcut is disabled unless `DJANGO_ENABLE_ENV_SUPERUSER=true`.
- Security headers include CSP, Permissions Policy, Cross-Origin Opener Policy, clickjacking protection, and no-sniff protection.

## Operating Standard

1. Keep all secrets in environment variables or a secret manager, never in source control.
2. Run local development with `DJANGO_DEBUG=true`; run every shared/staging/production environment with `DJANGO_DEBUG=false`.
3. Use PostgreSQL or another managed database for production instead of the checked-in SQLite file.
4. Keep uploaded media outside the repo, back it up separately, and serve it through controlled infrastructure.
5. Rotate attendance device API keys when a device is lost, reassigned, or suspected of exposure.
6. Add new file upload fields through `SecureModelForm` or equivalent validation, with explicit extension and size rules.
7. Run `python manage.py check --deploy` before deployment, plus `python manage.py test` before release.

## Accreditation Readiness

Formal accreditation requires choosing a target framework and keeping evidence, not only changing code. For ISO 27001, SOC 2, or a government security review, prepare these artifacts before assessment:

1. Asset register, data classification, and data-flow diagrams for employee, payroll, client, contract, and attendance records.
2. Access-control matrix covering system admin, manager, supervisor, HR, finance, and client-viewer roles.
3. Password, MFA, onboarding, offboarding, privileged-access, and device-token rotation procedures.
4. Backup, restore, disaster-recovery, incident-response, vulnerability-management, and patch-management procedures.
5. Audit logging and log-retention policy, including who reviews logs and how exceptions are escalated.
6. Evidence from dependency scans, static analysis, deployment checks, penetration testing, and restore drills.
7. Data-protection impact assessment and privacy notice aligned with the jurisdictions where the company operates.
