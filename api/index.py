import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "security_management.settings")

from security_management.wsgi import application  # noqa: E402

app = application
