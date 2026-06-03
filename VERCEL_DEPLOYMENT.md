# Vercel Deployment Checklist

The app can run on Vercel, but it must not use local development defaults.

## Required Environment Variables

Set these in Vercel Project Settings > Environment Variables, then redeploy:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<long-random-production-secret>
DJANGO_ALLOWED_HOSTS=guard-management-erp.vercel.app,guard-management-9cjueoyro-turyatemba-silaj-s-projects.vercel.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://guard-management-erp.vercel.app,https://guard-management-9cjueoyro-turyatemba-silaj-s-projects.vercel.app
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<database>?sslmode=require
DJANGO_SUPERUSER_USERNAME=siraje
DJANGO_SUPERUSER_PASSWORD=siraje@2026
DJANGO_SUPERUSER_EMAIL=siraje@example.com
ERP_PERMANENT_LOGIN=false
```

Vercel normally also provides `VERCEL=1` and `VERCEL_URL`; the settings file now reads those automatically. The explicit variables above are still recommended because they make the production host policy clear.

If `DATABASE_URL` is missing, the app falls back to the bundled SQLite database copied into `/tmp` on Vercel so requests do not fail with a localhost PostgreSQL error. That fallback is temporary and not durable; every deployment or cold runtime can lose writes. Use PostgreSQL for real production data.

## Live Login

The local `db.sqlite3` password reset does not automatically update the live Vercel database/runtime. The live login is controlled by the `DJANGO_SUPERUSER_*` variables above. After setting or changing them in Vercel, redeploy the project.

Use this login after redeploy:

```text
Username: siraje
Password: siraje@2026
```

When the first matching login request reaches Vercel, `core.auth_backends.EnvSuperuserBackend` creates or updates that user and marks it active, staff, and superuser.

## How To Confirm It Worked

After redeploying, visit:

```text
https://guard-management-erp.vercel.app/healthz/
```

It should return JSON showing `debug: false`, the active session engine, allowed hosts, and whether the database can be opened.

For the live login to work, the health response should also show the deployment superuser variables are configured. If either superuser flag is false, set `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` in Vercel and redeploy.

If a `DisallowedHost` page still shows:

- `DEBUG=True`, Vercel is still using development settings or an old deployment.
- `ALLOWED_HOSTS=['127.0.0.1', 'localhost', 'testserver']`, the latest code/env variables are not active.
- The production domain must appear in `ALLOWED_HOSTS`.

## PostgreSQL Database

This project prefers PostgreSQL on Vercel. SQLite is only a temporary fallback when no hosted database is configured, and it should not be treated as live production storage.

Use one PostgreSQL URL in Vercel:

```text
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<database>?sslmode=require
```

The settings also understand `POSTGRES_URL`, `POSTGRES_URL_NON_POOLING`, or the separate `DJANGO_DB_ENGINE`, `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, and `DJANGO_DB_PORT` variables.

After setting the PostgreSQL URL, run migrations against that database:

```text
python manage.py migrate
python manage.py setup_admin_roles --assign-active-staff
```

If you use a managed database such as Neon, Supabase, Railway, Render, or Vercel Postgres, copy its pooled connection string into `DATABASE_URL`, keep `sslmode=require`, then redeploy.
