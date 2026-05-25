from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = "ERP Modules"

    def ready(self):
        from .db_runtime import ensure_writable_sqlite_database

        ensure_writable_sqlite_database()

        if not getattr(settings, "DISABLE_LAST_LOGIN_UPDATE", False):
            return
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.disconnect(update_last_login)
        user_logged_in.disconnect(dispatch_uid="update_last_login")
