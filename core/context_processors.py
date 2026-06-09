from django.urls import reverse

from .access import can_access_internal, can_manage_attendance, can_manage_roles, can_manage_slug, is_manager
from .crud import visible_grouped_registry


SIDEBAR_HIDDEN_SLUGS = {
    "assets",
    "guard-schedules",
    "attendance-records",
    "zone-employee-allocations",
    "zone-site-allocations",
}


def sidebar_grouped_registry(user):
    groups = {}
    for department, configs in visible_grouped_registry(user).items():
        visible_configs = [(slug, config) for slug, config in configs if slug not in SIDEBAR_HIDDEN_SLUGS]
        if visible_configs:
            groups[department] = visible_configs
    return groups


def selected_sidebar_groups(groups, selected_department):
    if selected_department and selected_department in groups:
        return {selected_department: groups[selected_department]}
    return groups


def nav_item(title, url, icon="fa-circle-dot"):
    return {"title": title, "url": url, "icon": icon}


def record_nav_item(user, slug, title, icon="fa-circle-dot"):
    if not can_manage_slug(user, slug):
        return None
    return nav_item(title, reverse("core:record_list", args=[slug]), icon)


def append_record_item(items, user, slug, title, icon="fa-circle-dot"):
    item = record_nav_item(user, slug, title, icon)
    if item:
        items.append(item)


def build_sidebar_nav(groups, can_manage_payroll, user):
    operations = []
    if is_manager(user):
        operations.append(nav_item("Dashboard", reverse("core:dashboard"), "fa-gauge-high"))
    if can_manage_attendance(user):
        operations.extend(
            [
                nav_item("Attendances", reverse("core:attendances"), "fa-calendar-check"),
                nav_item("Upload Roster", reverse("core:upload_duty_roster"), "fa-file-excel"),
            ]
        )
    append_record_item(operations, user, "deployments", "Deployments", "fa-people-arrows")
    append_record_item(operations, user, "sites", "Sites", "fa-location-dot")
    append_record_item(operations, user, "incidents", "Incidents", "fa-triangle-exclamation")
    append_record_item(operations, user, "patrol-logs", "Patrol Logs", "fa-route")

    human_resources = []
    append_record_item(human_resources, user, "employees", "Employees", "fa-id-card")
    append_record_item(human_resources, user, "recruitment-applications", "Recruitment", "fa-user-plus")
    append_record_item(human_resources, user, "trainings", "Training", "fa-graduation-cap")
    append_record_item(human_resources, user, "leaves", "Leave Requests", "fa-person-walking-arrow-right")
    append_record_item(human_resources, user, "disciplinary-actions", "Discipline", "fa-scale-balanced")
    if can_manage_payroll:
        human_resources.insert(0, nav_item("Payroll", reverse("core:payroll"), "fa-money-check-dollar"))

    finance = []
    append_record_item(finance, user, "invoices", "Invoices", "fa-file-invoice")
    append_record_item(finance, user, "payments", "Payments", "fa-money-bill-transfer")
    append_record_item(finance, user, "expenses", "Expenses", "fa-receipt")
    append_record_item(finance, user, "advances", "Advances", "fa-hand-holding-dollar")
    append_record_item(finance, user, "budgets", "Budgets", "fa-chart-pie")
    append_record_item(finance, user, "accounts", "Chart of Accounts", "fa-book")

    reports = []
    if is_manager(user):
        reports.append(nav_item("Reports Center", reverse("core:reports_center"), "fa-folder-open"))
    if can_manage_attendance(user):
        reports.append(nav_item("Attendance Report", reverse("core:attendance_report"), "fa-table-list"))
    if is_manager(user):
        reports.extend(
            [
                nav_item("Zonal Employees", reverse("core:zonal_guard_list"), "fa-map-location-dot"),
                nav_item("Zone Shift Summary", reverse("core:zone_shift_summary"), "fa-chart-column"),
            ]
        )
    if can_manage_slug(user, "assets"):
        reports.append(nav_item("Asset Report", reverse("core:asset_report"), "fa-boxes-stacked"))
    if can_manage_payroll:
        reports.extend(
            [
                nav_item("Trial Balance", reverse("core:trial_balance"), "fa-scale-balanced"),
                nav_item("Reconciliation", reverse("core:reconciliation_report"), "fa-code-compare"),
            ]
        )

    admin = [nav_item("Home", reverse("core:home"), "fa-house")]
    if can_manage_roles(user):
        admin.extend(
            [
                nav_item("Users", reverse("core:user_list"), "fa-user-shield"),
                nav_item("Roles", reverse("core:role_list"), "fa-users-gear"),
            ]
        )
    if user.is_superuser:
        admin.append(nav_item("System Admin", "/admin/", "fa-screwdriver-wrench"))

    return [
        group
        for group in [
            {"title": "Operations", "icon": "fa-building-shield", "items": operations},
            {"title": "Human Resources", "icon": "fa-users-gear", "items": human_resources},
            {"title": "Finance", "icon": "fa-file-invoice-dollar", "items": finance},
            {"title": "Reports", "icon": "fa-folder-open", "items": reports},
            {"title": "Admin", "icon": "fa-shield-halved", "items": admin},
        ]
        if group["items"]
    ]


def mark_active_nav(nav_groups, path):
    for group in nav_groups:
        group["is_active"] = False
        for item in group["items"]:
            url = item["url"]
            is_active = path == url or (url != "/" and path.startswith(url))
            item["is_active"] = is_active
            if is_active:
                group["is_active"] = True
    return nav_groups


def sidebar_menu(request):
    user = request.user
    if not can_access_internal(user):
        return {
            "sidebar_model_groups": {},
            "sidebar_departments": [],
            "sidebar_active_department": "",
            "sidebar_nav_groups": [],
            "can_manage_payroll": False,
            "current_tenant": None,
            "current_tenant_membership": None,
        }

    groups = sidebar_grouped_registry(user)
    active_department = request.GET.get("department", "").strip()
    if active_department not in groups:
        active_department = ""

    can_manage_payroll = is_manager(user)
    sidebar_nav_groups = mark_active_nav(build_sidebar_nav(groups, can_manage_payroll, user), request.path)

    return {
        "sidebar_model_groups": selected_sidebar_groups(groups, active_department),
        "sidebar_departments": list(groups.keys()),
        "sidebar_active_department": active_department,
        "sidebar_nav_groups": sidebar_nav_groups,
        "can_manage_payroll": can_manage_payroll,
        "current_tenant": getattr(request, "tenant", None),
        "current_tenant_membership": getattr(request, "tenant_membership", None),
    }
