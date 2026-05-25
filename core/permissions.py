from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

from .access import SYSTEM_ADMIN_GROUP


def sync_system_admin_role(assign_active_staff=False):
    """Create a non-superuser admin role with full model permissions."""
    group, _created = Group.objects.get_or_create(name=SYSTEM_ADMIN_GROUP)
    group.permissions.set(Permission.objects.all())

    assigned_users = []
    if assign_active_staff:
        User = get_user_model()
        staff_users = User.objects.filter(is_active=True, is_staff=True)
        for user in staff_users:
            user.is_superuser = False
            user.groups.add(group)
            user.save(update_fields=["is_superuser"])
            assigned_users.append(user.username)

    return group, assigned_users
