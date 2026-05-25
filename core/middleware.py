from html import escape

from django.db import DatabaseError, OperationalError
from django.http import HttpResponse
from django.http import JsonResponse

from .db_runtime import ensure_writable_sqlite_database


class DatabaseErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ensure_writable_sqlite_database()
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, (DatabaseError, OperationalError)):
            return None

        message = (
            "The ERP database could not complete this request. "
            "If this is running on Vercel with SQLite, authenticated workflows need a hosted database such as PostgreSQL."
        )
        if request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse(
                {
                    "status": "error",
                    "message": message,
                    "detail": str(exception),
                },
                status=503,
            )
        return HttpResponse(
            (
                "<!doctype html><html><head><title>Database request failed</title>"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                "<style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.5;color:#172033}"
                ".box{max-width:760px}.detail{background:#fff3cd;border:1px solid #ffe69c;padding:12px;"
                "overflow-wrap:anywhere}</style></head><body><main class=\"box\">"
                "<h1>Database request failed</h1>"
                f"<p>{message}</p>"
                f"<div class=\"detail\">{escape(str(exception))}</div>"
                "<p>Open <a href=\"/healthz/\">/healthz/</a> to confirm the active database backend.</p>"
                "</main></body></html>"
            ),
            status=503,
            content_type="text/html; charset=utf-8",
        )
