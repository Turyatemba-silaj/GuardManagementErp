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
DJANGO_SUPERUSER_USERNAME=<admin-username>
DJANGO_SUPERUSER_PASSWORD=<long-random-temporary-bootstrap-password>
DJANGO_SUPERUSER_EMAIL=<admin-email>
DJANGO_ENABLE_ENV_SUPERUSER=false
DJANGO_HEALTHCHECK_TOKEN=<long-random-healthcheck-token>
ERP_PERMANENT_LOGIN=false
```

Vercel normally also provides `VERCEL=1` and `VERCEL_URL`; the settings file now reads those automatically. The explicit variables above are still recommended because they make the production host policy clear.

If `DATABASE_URL` is missing, the app falls back to the bundled SQLite database copied into `/tmp` on Vercel so requests do not fail with a localhost PostgreSQL error. That fallback is temporary and not durable; every deployment or cold runtime can lose writes. Use PostgreSQL for real production data.

## Bootstrap Login

The local `db.sqlite3` password reset does not automatically update the live Vercel database/runtime. The live login is controlled by the `DJANGO_SUPERUSER_*` variables above. After setting or changing them in Vercel, redeploy the project.

For a one-time bootstrap only:

1. Set `DJANGO_ENABLE_ENV_SUPERUSER=true`.
2. Redeploy.
3. Log in with the configured bootstrap username and temporary password.
4. Create a normal superuser or update the password in Django admin.
5. Set `DJANGO_ENABLE_ENV_SUPERUSER=false`, rotate `DJANGO_SUPERUSER_PASSWORD`, and redeploy again.

When enabled, `core.auth_backends.EnvSuperuserBackend` creates or updates that user and marks it active, staff, and superuser. Keep it disabled during normal production operation.

## How To Confirm It Worked

After redeploying, visit:

```text
https://guard-management-erp.vercel.app/healthz/
```

It should return minimal JSON with `status`, `database`, and `database_writable`.

For detailed diagnostics, send the configured token as `X-Healthcheck-Token`. Do not put detailed health output on a public dashboard.

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
