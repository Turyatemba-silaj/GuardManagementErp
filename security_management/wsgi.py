"""
WSGI config for security_management project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import traceback

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'security_management.settings')

try:
    application = get_wsgi_application()
except Exception as startup_error:
    traceback.print_exc()
    startup_error_text = f"{startup_error.__class__.__name__}: {startup_error}"

    def application(environ, start_response):
        expose_detail = os.environ.get("DJANGO_EXPOSE_STARTUP_ERRORS", "").strip().lower() in {"1", "true", "yes", "on"}
        body = b"Application startup failed. Check the Vercel Function logs for the Python traceback."
        if expose_detail:
            body = f"Application startup failed: {startup_error_text}".encode("utf-8")
        start_response(
            "500 Internal Server Error",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]
