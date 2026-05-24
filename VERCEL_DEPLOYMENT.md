# Vercel Deployment Checklist

The app can run on Vercel, but it must not use local development defaults.

## Required Environment Variables

Set these in Vercel Project Settings > Environment Variables, then redeploy:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<long-random-production-secret>
DJANGO_ALLOWED_HOSTS=guard-management-erp.vercel.app,guard-management-9cjueoyro-turyatemba-silaj-s-projects.vercel.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://guard-management-erp.vercel.app,https://guard-management-9cjueoyro-turyatemba-silaj-s-projects.vercel.app
DJANGO_SUPERUSER_USERNAME=siraje
DJANGO_SUPERUSER_PASSWORD=<temporary-strong-password>
DJANGO_SUPERUSER_EMAIL=<your-email>
```

Vercel normally also provides `VERCEL=1` and `VERCEL_URL`; the settings file now reads those automatically. The explicit variables above are still recommended because they make the production host policy clear.

## How To Confirm It Worked

After redeploying, visit:

```text
https://guard-management-erp.vercel.app/healthz/
```

It should return JSON showing `debug: false`, the active session engine, allowed hosts, and whether the database can be opened.

If a `DisallowedHost` page still shows:

- `DEBUG=True`, Vercel is still using development settings or an old deployment.
- `ALLOWED_HOSTS=['127.0.0.1', 'localhost', 'testserver']`, the latest code/env variables are not active.
- The production domain must appear in `ALLOWED_HOSTS`.

## Important Vercel Limitation

This project currently defaults to SQLite. SQLite inside a Vercel deployment is not a reliable production database because serverless deployments have an immutable/ephemeral filesystem. Use PostgreSQL for production and configure:

```text
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=<database>
DJANGO_DB_USER=<user>
DJANGO_DB_PASSWORD=<password>
DJANGO_DB_HOST=<host>
DJANGO_DB_PORT=5432
```

If PostgreSQL is used, add the required database driver to `requirements.txt`.

For short-term Vercel testing, the app uses signed-cookie sessions on Vercel, disables the automatic `last_login` database write, and can authenticate an existing bundled user with `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`. Any real data changes still require a writable production database.
