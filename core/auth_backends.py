import os
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EnvSuperuserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        env_username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        env_password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not env_username or not env_password or not username or not password:
            return None
        if not secrets.compare_digest(str(username), env_username):
            return None
        if not secrets.compare_digest(str(password), env_password):
            return None
        User = get_user_model()
        try:
            user = User.objects.get(username=env_username, is_active=True)
        except User.DoesNotExist:
            return None
        return user
