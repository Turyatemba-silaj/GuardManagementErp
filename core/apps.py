import os
import warnings

from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        if not getattr(settings, "DISABLE_LAST_LOGIN_UPDATE", False):
            self.ensure_deployment_superuser()
            return
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.disconnect(update_last_login)
        self.ensure_deployment_superuser()

    def ensure_deployment_superuser(self):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        if not username or not password:
            return
        try:
            from django.contrib.auth import get_user_model
            from django.db import OperationalError, ProgrammingError

            User = get_user_model()
            user, _created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_staff": True, "is_superuser": True, "is_active": True},
            )
            user.email = email or user.email
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save(update_fields=["email", "is_staff", "is_superuser", "is_active", "password"])
        except (OperationalError, ProgrammingError) as error:
            warnings.warn(f"Could not create deployment superuser: {error}", RuntimeWarning)
