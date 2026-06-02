from django.urls import reverse

from .access import can_access_internal, can_manage_attendance, can_manage_slug, is_manager
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


def model_nav_items(configs):
    items = []
    for slug, config in configs:
        if slug == "guard-schedules":
            url = reverse("core:attendances")
        else:
            url = reverse("core:record_list", args=[slug])
        items.append(nav_item(config.title, url, "fa-circle-dot"))
    return items


def build_sidebar_nav(groups, can_manage_payroll, user):
    operations_models = model_nav_items(groups.get("Operations", []))
    hr_models = model_nav_items(groups.get("Human Resource", []))
    finance_models = model_nav_items(groups.get("Finance", []))

    operations = []
    if is_manager(user):
        operations.append(nav_item("Command Dashboard", reverse("core:dashboard"), "fa-gauge-high"))
    if can_manage_attendance(user):
        operations.extend(
            [
                nav_item("Attendances", reverse("core:attendances"), "fa-calendar-check"),
                nav_item("Upload Scheduled Guards", reverse("core:upload_duty_roster"), "fa-file-excel"),
            ]
        )
    operations.extend(operations_models)

    human_resources = [
        *hr_models,
    ]
    if can_manage_payroll:
        human_resources.insert(0, nav_item("Payroll", reverse("core:payroll"), "fa-money-check-dollar"))

    finance = [
        *finance_models,
    ]

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
                nav_item("Audit Report", reverse("core:audit_report"), "fa-clipboard-check"),
                nav_item("General Ledger", reverse("core:general_ledger"), "fa-book"),
                nav_item("Trial Balance", reverse("core:trial_balance"), "fa-scale-balanced"),
                nav_item("Balance Sheet", reverse("core:balance_sheet"), "fa-table-columns"),
                nav_item("Income Statement", reverse("core:income_statement"), "fa-chart-line"),
                nav_item("Receivables Aging", reverse("core:receivables_aging"), "fa-clock-rotate-left"),
                nav_item("Reconciliation", reverse("core:reconciliation_report"), "fa-code-compare"),
                nav_item("Payroll Reconciliation", reverse("core:payroll_reconciliation_report"), "fa-money-check-dollar"),
                nav_item("Expense Reconciliation", reverse("core:expense_reconciliation_report"), "fa-receipt"),
                nav_item("Payment Reconciliation", reverse("core:payment_reconciliation_report"), "fa-money-bill-transfer"),
            ]
        )

    admin = [nav_item("Public Home", reverse("core:home"), "fa-house")]
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
