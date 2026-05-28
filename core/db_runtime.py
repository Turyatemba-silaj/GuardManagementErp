import os
import shutil
from pathlib import Path

from django.conf import settings
from django.db import connections


def is_vercel_runtime():
    return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV") or os.environ.get("VERCEL_URL"))


def using_sqlite():
    return settings.DATABASES["default"].get("ENGINE") == "django.db.backends.sqlite3"


def sqlite_path():
    name = settings.DATABASES["default"].get("NAME", "")
    return Path(name) if name else None


def sqlite_needs_writable_runtime_copy(path):
    if not path:
        return False
    path_text = str(path).replace("\\", "/")
    return path_text.startswith("/var/task/") or path_text.startswith(str(settings.BASE_DIR).replace("\\", "/"))


def ensure_writable_sqlite_database():
    if not is_vercel_runtime() or not using_sqlite():
        return False

    current_path = sqlite_path()
    if not sqlite_needs_writable_runtime_copy(current_path):
        return False

    writable_path = Path(os.environ.get("DJANGO_SQLITE_TMP_NAME", "/tmp/erp.sqlite3"))
    writable_path.parent.mkdir(parents=True, exist_ok=True)
    if current_path and current_path.exists() and (
        not writable_path.exists() or current_path.stat().st_mtime > writable_path.stat().st_mtime
    ):
        shutil.copy2(current_path, writable_path)

    settings.DATABASES["default"]["NAME"] = str(writable_path)
    connections["default"].close()
    return True
