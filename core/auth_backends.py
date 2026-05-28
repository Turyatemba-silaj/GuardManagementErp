import os
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EnvSuperuserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
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
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=env_username,
            defaults={
                "email": env_email,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        changed_fields = []
        if created or not user.check_password(env_password):
            user.set_password(env_password)
            changed_fields.append("password")
        if env_email and user.email != env_email:
            user.email = env_email
            changed_fields.append("email")
        for field in ("is_active", "is_staff", "is_superuser"):
            if not getattr(user, field):
                setattr(user, field, True)
                changed_fields.append(field)
        if changed_fields:
            user.save(update_fields=changed_fields)
        return user
