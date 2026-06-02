from html import escape

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth.views import redirect_to_login
from django.db import DatabaseError, OperationalError
from django.http import HttpResponse
from django.http import JsonResponse
from django.middleware.csrf import rotate_token

from .auth_backends import ensure_superuser
from .db_runtime import ensure_writable_sqlite_database


class SaaSTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.tenant_membership = None
        if request.user.is_authenticated:
            from .models import TenantMembership, TenantOrganization

            host = request.get_host().split(":", 1)[0].lower()
            membership = None
            if host:
                membership = (
                    TenantMembership.objects.select_related("organization", "organization__plan")
                    .filter(
                        user=request.user,
                        is_active=True,
                        organization__primary_domain__iexact=host,
                    )
                    .first()
                )
            active_tenant_id = request.session.get("active_tenant_id")
            if not membership and active_tenant_id:
                membership = (
                    TenantMembership.objects.select_related("organization", "organization__plan")
                    .filter(user=request.user, is_active=True, organization_id=active_tenant_id)
                    .first()
                )
            if not membership:
                membership = (
                    TenantMembership.objects.select_related("organization", "organization__plan")
                    .filter(user=request.user, is_active=True)
                    .order_by("organization__name")
                    .first()
                )
            if membership:
                request.tenant_membership = membership
                request.tenant = membership.organization
            elif request.user.is_superuser:
                request.tenant = TenantOrganization.objects.select_related("plan").order_by("name").first()
        return self.get_response(request)


class PermanentLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "ERP_PERMANENT_LOGIN", False) and not request.user.is_authenticated:
            user = ensure_superuser(
                username=getattr(settings, "ERP_PERMANENT_LOGIN_USERNAME", "admin"),
                password=getattr(settings, "ERP_PERMANENT_LOGIN_PASSWORD", ""),
                email=getattr(settings, "ERP_PERMANENT_LOGIN_EMAIL", ""),
            )
            request.session[SESSION_KEY] = str(user.pk)
            request.session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
            request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
            request.session.set_expiry(getattr(settings, "ERP_PERMANENT_LOGIN_AGE", 315360000))
            request.user = user
            rotate_token(request)
        return self.get_response(request)


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_prefixes = tuple(
            getattr(
                settings,
                "LOGIN_EXEMPT_URL_PREFIXES",
                (
                    settings.LOGIN_URL,
                    "/accounts/",
                    "/admin/login/",
                    "/static/",
                    settings.MEDIA_URL,
                    "/healthz/",
                    "/api/attendance/swipe/",
                ),
            )
        )

    def __call__(self, request):
        if request.user.is_authenticated or self.is_public_path(request.path):
            return self.get_response(request)
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)

    def is_public_path(self, path):
        return any(path.startswith(prefix) for prefix in self.public_prefixes if prefix)


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
