from django.conf import settings

HR_MANAGER_GROUP = "Human Resources Manager"
MANAGER_GROUP = "Manager"
SYSTEM_ADMIN_GROUP = "System Administrator"
SUPERVISOR_GROUP = "Supervisor"
GUARD_GROUP = "Guard"
ATTENDANCE_SUPERVISOR_GROUP = "Attendance Supervisor"
OPERATIONS_LIMITED_MANAGER_GROUP = "Operations Limited Manager"

ATTENDANCE_ALLOWED_SLUGS = {
    "guard-schedules",
    "roster-attendances",
    "attendance-records",
}

LIMITED_MANAGER_ALLOWED_SLUGS = ATTENDANCE_ALLOWED_SLUGS | {
    "assets",
    "incidents",
}

SUPERVISOR_ALLOWED_SLUGS = {
    "guard-schedules",
    "roster-attendances",
    "attendance-records",
    "assets",
    "zones",
    "zone-employee-allocations",
    "zone-site-allocations",
    "sites",
    "employees",
}


def in_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_hr_manager(user):
    return user.is_authenticated and (user.is_superuser or in_group(user, SYSTEM_ADMIN_GROUP) or in_group(user, HR_MANAGER_GROUP))


def is_manager(user):
    return user.is_authenticated and (
        user.is_superuser or in_group(user, SYSTEM_ADMIN_GROUP) or in_group(user, MANAGER_GROUP) or in_group(user, HR_MANAGER_GROUP)
    )


def can_manage_roles(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or in_group(user, SYSTEM_ADMIN_GROUP):
        return True
    return user.has_perm("auth.view_group") and user.has_perm("auth.change_group") and user.has_perm("auth.change_user")


def is_supervisor(user):
    return user.is_authenticated and (user.is_superuser or in_group(user, SUPERVISOR_GROUP))


def is_attendance_supervisor(user):
    return user.is_authenticated and in_group(user, ATTENDANCE_SUPERVISOR_GROUP)


def is_limited_operations_manager(user):
    return user.is_authenticated and in_group(user, OPERATIONS_LIMITED_MANAGER_GROUP)


def can_manage_attendance(user):
    return is_manager(user) or is_supervisor(user) or is_attendance_supervisor(user) or is_limited_operations_manager(user)


def can_access_internal(user):
    if not user.is_authenticated:
        return False
    if getattr(settings, "SAAS_ENFORCE_TENANT_ACCESS", False) and not user.is_superuser:
        has_active_tenant = user.tenant_memberships.filter(
            is_active=True,
            organization__status__in=["trialing", "active"],
        ).exists()
        if not has_active_tenant:
            return False
    return (
        user.is_staff
        or is_manager(user)
        or is_supervisor(user)
        or is_attendance_supervisor(user)
        or is_limited_operations_manager(user)
        or in_group(user, GUARD_GROUP)
        or bool(user.get_all_permissions())
    )


def has_model_perm(user, slug, action):
    if not user.is_authenticated:
        return False
    try:
        from .crud import MODEL_REGISTRY

        config = MODEL_REGISTRY.get(slug)
        if not config:
            return False
        opts = config.model._meta
        return user.has_perm(f"{opts.app_label}.{action}_{opts.model_name}")
    except Exception:
        return False


def can_manage_slug(user, slug):
    if is_manager(user):
        return True
    if is_limited_operations_manager(user):
        return slug in LIMITED_MANAGER_ALLOWED_SLUGS
    if is_attendance_supervisor(user):
        return slug in ATTENDANCE_ALLOWED_SLUGS
    if is_supervisor(user):
        return slug in SUPERVISOR_ALLOWED_SLUGS
    return any(has_model_perm(user, slug, action) for action in ("view", "add", "change", "delete"))


def supervisor_profile_for(user):
    if not user.is_authenticated:
        return None
    try:
        return user.employee_profile
    except Exception:
        return None
