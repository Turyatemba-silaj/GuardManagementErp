import os

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_security_configuration(app_configs, **kwargs):
    errors = []
    configured_secret = os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not settings.DEBUG and not configured_secret:
        errors.append(
            Error(
                "DJANGO_SECRET_KEY or SECRET_KEY is required when DJANGO_DEBUG is false.",
                hint="Set a long random secret in the deployment environment.",
                id="erp_security.E001",
            )
        )
    if not settings.DEBUG and settings.SECRET_KEY == "dev-only-insecure-change-me":
        errors.append(
            Error(
                "Production is using the development SECRET_KEY.",
                hint="Set DJANGO_SECRET_KEY or SECRET_KEY to a long random value.",
                id="erp_security.E002",
            )
        )
    if (
        getattr(settings, "ERP_PERMANENT_LOGIN", False)
        and not settings.DEBUG
        and not os.environ.get("DJANGO_ALLOW_INSECURE_PERMANENT_LOGIN", "").lower() in {"1", "true", "yes", "on"}
    ):
        errors.append(
            Error(
                "ERP_PERMANENT_LOGIN is enabled in production.",
                hint="Set ERP_PERMANENT_LOGIN=false for shared or live deployments.",
                id="erp_security.E003",
            )
        )
    return errors
