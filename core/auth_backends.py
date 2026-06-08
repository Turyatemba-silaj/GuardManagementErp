import os
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def ensure_superuser(username=None, password=None, email=""):
    username = username or os.environ.get("DJANGO_SUPERUSER_USERNAME") or "admin"
    password = password or os.environ.get("DJANGO_SUPERUSER_PASSWORD") or ""
    email = email if email is not None else os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    changed_fields = []
    if password and (created or not user.check_password(password)):
        user.set_password(password)
        changed_fields.append("password")
    if email and user.email != email:
        user.email = email
        changed_fields.append("email")
    for field in ("is_active", "is_staff", "is_superuser"):
        if not getattr(user, field):
            setattr(user, field, True)
            changed_fields.append(field)
    if changed_fields:
        user.save(update_fields=changed_fields)
    return user


class EnvSuperuserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not getattr(settings, "DJANGO_ENABLE_ENV_SUPERUSER", False):
            return None
        env_username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        env_password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        env_email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        login_identifier = username or kwargs.get(get_user_model().USERNAME_FIELD)
        if not env_username or not env_password or not login_identifier or not password:
            return None
        allowed_identifiers = [env_username]
        if env_email:
            allowed_identifiers.append(env_email)
        if not any(secrets.compare_digest(str(login_identifier), identifier) for identifier in allowed_identifiers):
            return None
        if not secrets.compare_digest(str(password), env_password):
            return None
        return ensure_superuser(username=env_username, password=env_password, email=env_email)
