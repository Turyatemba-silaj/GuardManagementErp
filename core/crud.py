from dataclasses import dataclass

from . import models


@dataclass(frozen=True)
class ModelConfig:
    model: type
    title: str
    department: str
    columns: tuple[str, ...]


MODEL_REGISTRY = {
    "clients": ModelConfig(models.Client, "Clients", "Operations", ("client_name", "contact_person", "phone_number", "contract_status")),
    "contracts": ModelConfig(models.Contract, "Contracts", "Operations", ("contract_number", "client", "service_type", "required_guards", "start_date", "end_date", "billing_rate", "status")),
    "contract-site-requirements": ModelConfig(
        models.ContractSiteRequirement,
        "Contract Site Requirements",
        "Operations",
        (
            "contract",
            "site",
            "shift",
            "required_guards",
            "rate_per_guard",
            "gun_count",
            "radio_count",
            "metal_detector_count",
            "walk_through_machine_count",
            "dog_count",
            "start_date",
            "end_date",
            "status",
        ),
    ),
    "sites": ModelConfig(
        models.Site,
        "Sites",
        "Operations",
        (
            "site_code",
            "site_name",
            "client",
            "city",
            "security_level",
            "latitude",
            "longitude",
            "geofence_radius_meters",
            "required_guards_per_shift",
        ),
    ),
    "shifts": ModelConfig(models.Shift, "Shifts", "Operations", ("shift_name", "code", "start_time", "end_time", "duration_hours", "basic_hours", "daily_overtime_hours")),
    "deployments": ModelConfig(
        models.Deployment,
        "Deployments",
        "Operations",
        ("employee_number", "employee", "client", "site", "shift", "start_date", "status"),
    ),
    "guard-schedules": ModelConfig(models.GuardSchedule, "Guard Schedules", "Operations", ("employee", "replacement_employee", "site", "shift", "shift_date", "status")),
    "incidents": ModelConfig(models.Incident, "Incidents", "Operations", ("incident_type", "deployment", "employee", "incident_date", "severity_level", "status")),
    "patrol-logs": ModelConfig(models.PatrolLog, "Patrol Logs", "Operations", ("employee", "site", "patrol_time", "patrol_route")),
    "assets": ModelConfig(models.Asset, "Assets", "Operations", ("asset_name", "asset_type", "serial_number", "quantity", "condition", "assigned_to")),
    "employees": ModelConfig(
        models.Employee,
        "Employees",
        "Human Resource",
        (
            "company_number",
            "work_card_uid",
            "full_name",
            "role",
            "position",
            "phone_number",
            "date_of_birth",
            "gender",
            "email",
            "bank_account",
            "national_id",
            "nssf_number",
            "hire_date",
            "status",
            "qualification",
            "training_level",
            "assigned_zone",
            "experience_years",
        ),
    ),
    "roles": ModelConfig(models.Role, "Roles", "Human Resource", ("role_name", "department")),
    "positions": ModelConfig(models.Position, "Positions", "Human Resource", ("position_title", "department", "grade_level", "salary_range_min", "salary_range_max")),
    "zones": ModelConfig(models.Zone, "Zones", "Operations", ("zone_code", "zone_name", "supervisor", "status")),
    "zone-employee-allocations": ModelConfig(models.ZoneEmployeeAllocation, "Zone Employee Allocations", "Operations", ("zone", "employee", "start_date", "end_date", "status")),
    "zone-site-allocations": ModelConfig(models.ZoneSiteAllocation, "Zone Site Allocations", "Operations", ("zone", "site", "start_date", "end_date", "status")),
    "trainings": ModelConfig(
        models.Training,
        "Trainings",
        "Human Resource",
        (
            "employee",
            "training_name",
            "training_type",
            "provider",
            "trainer_name",
            "venue",
            "start_date",
            "end_date",
            "duration_hours",
            "result",
            "score",
            "certificate_no",
            "expiry_date",
            "next_refresh_date",
            "budgeted_cost",
            "training_cost",
            "status",
        ),
    ),
    "recruitment-requisitions": ModelConfig(
        models.RecruitmentRequisition,
        "Recruitment Requisitions",
        "Human Resource",
        (
            "requisition_number",
            "vacancy_title",
            "department",
            "position",
            "requested_by",
            "number_of_openings",
            "employment_type",
            "work_location",
            "opening_date",
            "closing_date",
            "applications_count",
            "hired_count",
            "recruitment_budget",
            "actual_recruitment_cost",
            "status",
        ),
    ),
    "recruitment-applications": ModelConfig(
        models.RecruitmentApplication,
        "Recruitment Applications",
        "Human Resource",
        (
            "full_name",
            "requisition",
            "application_source",
            "date_received",
            "phone_number",
            "email",
            "highest_qualification",
            "years_experience",
            "screening_score",
            "background_check_status",
            "status",
        ),
    ),
    "recruitment-interviews": ModelConfig(
        models.RecruitmentInterview,
        "Recruitment Interviews",
        "Human Resource",
        (
            "application",
            "interview_type",
            "scheduled_at",
            "venue_or_link",
            "interviewer",
            "score",
            "recommendation",
            "status",
        ),
    ),
    "job-offers": ModelConfig(
        models.JobOffer,
        "Job Offers",
        "Human Resource",
        (
            "application",
            "offered_position",
            "offer_date",
            "expected_start_date",
            "salary_offer",
            "contract_type",
            "status",
        ),
    ),
    "attendance-records": ModelConfig(
        models.Attendance,
        "Attendance Records",
        "Human Resource",
        (
            "employee",
            "schedule",
            "shift",
            "date",
            "time_in",
            "time_out",
            "status",
            "capture_source",
            "device_id",
            "geofence_distance_meters",
        ),
    ),
    "attendance-devices": ModelConfig(
        models.AttendanceDevice,
        "Attendance Devices",
        "Operations",
        ("device_id", "name", "assigned_site", "assigned_supervisor", "is_active"),
    ),
    "attendance-device-events": ModelConfig(
        models.AttendanceDeviceEvent,
        "Attendance Device Events",
        "Operations",
        (
            "event_timestamp",
            "device_identifier",
            "card_uid",
            "employee",
            "site",
            "event_type",
            "status",
            "geofence_distance_meters",
            "message",
        ),
    ),
    "leaves": ModelConfig(models.Leave, "Leave Requests", "Human Resource", ("employee", "leave_type", "start_date", "end_date", "approval_status")),
    "disciplinary-actions": ModelConfig(models.DisciplinaryAction, "Disciplinary Actions", "Human Resource", ("employee", "action_type", "action_date", "penalty", "status")),
    "performance-evaluations": ModelConfig(models.PerformanceEvaluation, "Performance Evaluations", "Human Resource", ("employee", "eval_date", "rating", "evaluated_by")),
    "documents": ModelConfig(models.Document, "Documents", "Human Resource", ("employee", "doc_type", "issue_date", "expiry_date")),
    "salaries": ModelConfig(
        models.Salary,
        "Salaries",
        "Human Resource",
        (
            "employee",
            "pay_period_start",
            "pay_period_end",
            "attendance_days",
            "basic_hours",
            "overtime_hours",
            "basic_salary",
            "overtime_pay",
            "gross_pay",
            "nssf_employee",
            "nssf_employer",
            "total_deductions",
            "net_salary",
            "status",
        ),
    ),
    "advances": ModelConfig(models.Advance, "Advances", "Finance", ("employee", "request_date", "amount_requested", "approval_status", "repayment_status")),
    "invoices": ModelConfig(
        models.Invoice,
        "Invoices",
        "Finance",
        (
            "invoice_number",
            "client",
            "billing_scope",
            "site",
            "billing_month",
            "guard_count",
            "rate_per_guard",
            "subtotal_amount",
            "vat_amount",
            "total_amount",
            "balance_amount",
            "status",
        ),
    ),
    "payments": ModelConfig(models.Payment, "Payments", "Finance", ("payment_date", "invoice", "employee", "amount", "payment_method")),
    "accounts": ModelConfig(models.Account, "Accounts", "Finance", ("account_code", "account_name", "account_type", "parent_account", "is_active")),
    "journal-entries": ModelConfig(models.JournalEntry, "Journal Entries", "Finance", ("entry_date", "reference", "source_module", "total_debit", "total_credit", "status")),
    "journal-lines": ModelConfig(models.JournalLine, "Journal Lines", "Finance", ("journal_entry", "account", "debit", "credit", "description")),
    "budgets": ModelConfig(models.Budget, "Budgets", "Finance", ("year", "department", "category", "allocated_amount", "spent_amount", "remaining_amount")),
    "expenses": ModelConfig(models.Expense, "Expenses", "Finance", ("expense_date", "category", "amount", "approved_by", "receipt_no")),
}


def grouped_registry():
    groups = {}
    for slug, config in MODEL_REGISTRY.items():
        groups.setdefault(config.department, []).append((slug, config))
    return groups


def visible_grouped_registry(user):
    from .access import can_manage_slug

    groups = {}
    for department, configs in grouped_registry().items():
        visible_configs = [(slug, config) for slug, config in configs if can_manage_slug(user, slug)]
        if visible_configs:
            groups[department] = visible_configs
    return groups
