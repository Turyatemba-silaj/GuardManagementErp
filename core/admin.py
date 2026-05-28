from django.contrib import admin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html

from . import models


admin.site.site_header = "System Admin"
admin.site.site_title = "System Admin"
admin.site.index_title = "System Admin"

User = get_user_model()
LogEntry._meta.verbose_name = "Activity log"
LogEntry._meta.verbose_name_plural = "Activity logs"

for auth_model in (User, Group):
    try:
        admin.site.unregister(auth_model)
    except NotRegistered:
        pass


@admin.register(User)
class SentinelUserAdmin(DjangoUserAdmin):
    list_display = ("username", "full_name", "email", "role_groups", "is_staff", "is_active", "last_login")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ("last_login", "date_joined")
    save_on_top = True

    fieldsets = (
        ("Account", {"fields": ("username", "password")}),
        ("Personal details", {"fields": ("first_name", "last_name", "email")}),
        ("Role assignment", {"fields": ("groups",), "description": "Assign one or more ERP roles. Role permissions are managed under Groups."}),
        ("Direct permissions", {"fields": ("user_permissions",), "description": "Assign permissions that apply only to this user."}),
        ("Access status", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            "Create user",
            {
                "classes": ("wide",),
                "fields": ("username", "usable_password", "password1", "password2"),
            },
        ),
        ("Role assignment", {"fields": ("groups",)}),
        ("Direct permissions", {"fields": ("user_permissions",)}),
        ("Access status", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.get_full_name() or "-"

    @admin.display(description="Roles")
    def role_groups(self, obj):
        groups = list(obj.groups.values_list("name", flat=True))
        return ", ".join(groups) if groups else "-"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("is_active", True)
        initial.setdefault("is_staff", True)
        return initial


@admin.register(Group)
class SentinelGroupAdmin(DjangoGroupAdmin):
    list_display = ("name", "permission_total", "user_total")
    search_fields = ("name", "permissions__name", "permissions__codename")
    filter_horizontal = ("permissions",)

    @admin.display(description="Permissions")
    def permission_total(self, obj):
        return obj.permissions.count()

    @admin.display(description="Users")
    def user_total(self, obj):
        return obj.user_set.count()


@admin.register(LogEntry)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action_time", "user", "action_badge", "content_type", "object_link", "change_summary")
    list_filter = ("action_flag", "content_type", "user", "action_time")
    search_fields = ("user__username", "user__first_name", "user__last_name", "object_repr", "change_message")
    readonly_fields = (
        "action_time",
        "user",
        "action_flag",
        "content_type",
        "object_id",
        "object_repr",
        "change_message",
        "change_summary",
        "object_link",
    )
    date_hierarchy = "action_time"
    ordering = ("-action_time",)
    list_per_page = 50

    @admin.display(description="Action", ordering="action_flag")
    def action_badge(self, obj):
        labels = {
            ADDITION: ("Added", "#0f8b6f"),
            CHANGE: ("Changed", "#2563eb"),
            DELETION: ("Deleted", "#c2413a"),
        }
        label, color = labels.get(obj.action_flag, ("Activity", "#667085"))
        return format_html(
            '<span style="display:inline-block;min-width:72px;padding:3px 8px;border-radius:999px;'
            'background:{}1a;color:{};font-weight:800;text-align:center;">{}</span>',
            color,
            color,
            label,
        )

    @admin.display(description="Record")
    def object_link(self, obj):
        if not obj.content_type_id or not obj.object_id or obj.action_flag == DELETION:
            return obj.object_repr or "-"
        try:
            url = reverse(
                f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                args=[obj.object_id],
            )
        except NoReverseMatch:
            return obj.object_repr or "-"
        return format_html('<a href="{}">{}</a>', url, obj.object_repr or obj.object_id)

    @admin.display(description="Details")
    def change_summary(self, obj):
        message = obj.get_change_message()
        return message or "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "content_type")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("client_name", "contact_person", "phone_number", "contract_status")
    list_filter = ("contract_status",)
    search_fields = ("client_name", "contact_person", "phone_number", "email")


@admin.register(models.Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "client",
        "service_type",
        "required_guards",
        "other_deliverables",
        "start_date",
        "end_date",
        "billing_rate",
        "status",
    )
    list_filter = ("status", "service_type")
    search_fields = ("contract_number", "client__client_name", "terms")
    date_hierarchy = "start_date"


@admin.register(models.ContractSiteRequirement)
class ContractSiteRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "contract",
        "site",
        "shift",
        "required_guards",
        "billing_rate",
        "gun_count",
        "radio_count",
        "metal_detector_count",
        "walk_through_machine_count",
        "dog_count",
        "panic_baton_count",
        "handcuffs_count",
        "billable_total",
        "start_date",
        "end_date",
        "status",
    )
    list_filter = ("status", "site", "shift")
    search_fields = ("contract__contract_number", "site__site_code", "site__site_name")


@admin.register(models.Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = (
        "site_code",
        "site_name",
        "client",
        "city",
        "security_level",
        "latitude",
        "longitude",
        "geofence_radius_meters",
        "required_guards_per_shift",
    )
    list_filter = ("city", "security_level")
    readonly_fields = ("site_code",)
    search_fields = ("site_code", "site_name", "client__client_name", "site_address")


@admin.register(models.Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_name", "department")
    list_filter = ("department",)
    search_fields = ("role_name",)


@admin.register(models.Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("position_title", "department", "grade_level", "salary_range_min", "salary_range_max")
    list_filter = ("department", "grade_level")
    search_fields = ("position_title",)


@admin.register(models.Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("company_number", "work_card_uid", "nssf_number", "full_name", "role", "position", "phone_number", "email", "bank_account", "status")
    list_filter = ("status", "role__department", "role", "position")
    search_fields = ("first_name", "last_name", "email", "phone_number", "national_id", "company_number", "work_card_uid", "nssf_number", "bank_account")


@admin.register(models.Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("zone_code", "zone_name", "supervisor", "status")
    list_filter = ("status", "supervisor")
    search_fields = ("zone_code", "zone_name", "supervisor__first_name", "supervisor__last_name")


@admin.register(models.ZoneEmployeeAllocation)
class ZoneEmployeeAllocationAdmin(admin.ModelAdmin):
    list_display = ("zone", "employee", "start_date", "end_date", "status", "allocated_by")
    list_filter = ("status", "zone")
    search_fields = ("zone__zone_name", "employee__company_number", "employee__first_name", "employee__last_name")


@admin.register(models.ZoneSiteAllocation)
class ZoneSiteAllocationAdmin(admin.ModelAdmin):
    list_display = ("zone", "site", "start_date", "end_date", "status", "allocated_by")
    list_filter = ("status", "zone")
    search_fields = ("zone__zone_name", "site__site_code", "site__site_name")


@admin.register(models.Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "shift_name",
        "code",
        "start_time",
        "end_time",
        "duration_hours",
        "basic_hours",
        "daily_overtime_hours",
        "normal_day_overtime_multiplier",
        "public_holiday_overtime_multiplier",
    )
    list_filter = ("code",)
    search_fields = ("shift_name", "code")


@admin.register(models.Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ("employee_number", "employee", "client", "site", "supervisor", "shift", "start_date", "status")
    list_filter = ("status", "shift", "client", "site")
    search_fields = ("employee__company_number", "employee__first_name", "employee__last_name", "client__client_name", "site__site_name")
    date_hierarchy = "start_date"


@admin.register(models.GuardSchedule)
class GuardScheduleAdmin(admin.ModelAdmin):
    list_display = ("employee", "replacement_employee", "site", "shift", "shift_date", "status")
    list_filter = ("status", "site", "shift", "shift_date")
    search_fields = ("employee__company_number", "employee__first_name", "employee__last_name", "site__site_name")
    date_hierarchy = "shift_date"


@admin.register(models.RosterAttendance)
class RosterAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "shift_date",
        "employee",
        "site",
        "shift",
        "import_status",
        "duty_code",
        "source_format",
        "source_row",
        "file_name",
    )
    list_filter = ("import_status", "source_format", "shift_date", "site", "shift")
    search_fields = (
        "batch_reference",
        "file_name",
        "employee__company_number",
        "employee__first_name",
        "employee__last_name",
        "site__site_code",
        "site__site_name",
        "message",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "shift_date"


@admin.register(models.Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("incident_type", "deployment", "employee", "incident_date", "severity_level", "status")
    list_filter = ("severity_level", "status", "incident_type")
    search_fields = ("incident_type", "description", "location", "employee__company_number")
    date_hierarchy = "incident_date"


@admin.register(models.PatrolLog)
class PatrolLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "site", "patrol_time", "patrol_route")
    list_filter = ("site",)
    search_fields = ("employee__company_number", "site__site_name", "patrol_route", "observations")
    date_hierarchy = "patrol_time"


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_name", "asset_type", "serial_number", "quantity", "condition", "assigned_to")
    list_filter = ("asset_type", "condition")
    search_fields = ("asset_name", "serial_number", "assigned_to__first_name", "assigned_to__last_name")


@admin.register(models.Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = (
        "training_name",
        "employee",
        "training_type",
        "provider",
        "trainer_name",
        "start_date",
        "end_date",
        "duration_hours",
        "result",
        "score",
        "expiry_date",
        "status",
    )
    list_filter = ("training_type", "result", "status", "provider", "start_date", "expiry_date")
    search_fields = (
        "training_name",
        "course_code",
        "employee__company_number",
        "employee__first_name",
        "employee__last_name",
        "provider",
        "trainer_name",
        "certificate_no",
    )
    date_hierarchy = "start_date"
    fieldsets = (
        (
            "Training Details",
            {
                "fields": (
                    "employee",
                    "training_name",
                    "course_code",
                    "training_type",
                    "training_objective",
                    "provider",
                    "trainer_name",
                    "trainer_contact",
                    "venue",
                )
            },
        ),
        (
            "Schedule and Cost",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "duration_hours",
                    "budgeted_cost",
                    "training_cost",
                    "approved_by",
                    "status",
                )
            },
        ),
        (
            "Assessment and Certification",
            {
                "fields": (
                    "pass_mark",
                    "score",
                    "result",
                    "certificate_no",
                    "certificate_file",
                    "expiry_date",
                    "next_refresh_date",
                    "action_notes",
                )
            },
        ),
    )


@admin.register(models.RecruitmentRequisition)
class RecruitmentRequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "requisition_number",
        "vacancy_title",
        "department",
        "position",
        "number_of_openings",
        "employment_type",
        "opening_date",
        "closing_date",
        "applications_count",
        "hired_count",
        "status",
    )
    list_filter = ("department", "employment_type", "status", "opening_date")
    search_fields = ("requisition_number", "vacancy_title", "position__position_title", "work_location")
    date_hierarchy = "opening_date"
    fieldsets = (
        (
            "Vacancy",
            {
                "fields": (
                    "requisition_number",
                    "vacancy_title",
                    "position",
                    "department",
                    "requested_by",
                    "number_of_openings",
                    "employment_type",
                    "work_location",
                    "status",
                )
            },
        ),
        (
            "Budget and Requirements",
            {
                "fields": (
                    "salary_budget_min",
                    "salary_budget_max",
                    "recruitment_budget",
                    "actual_recruitment_cost",
                    "minimum_qualification",
                    "experience_required",
                    "job_description",
                )
            },
        ),
        ("Timeline and Approval", {"fields": ("opening_date", "closing_date", "approval_notes")}),
    )


@admin.register(models.RecruitmentApplication)
class RecruitmentApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "requisition",
        "application_source",
        "date_received",
        "phone_number",
        "email",
        "screening_score",
        "status",
    )
    list_filter = ("application_source", "status", "date_received", "requisition")
    search_fields = (
        "first_name",
        "last_name",
        "phone_number",
        "email",
        "national_id",
        "requisition__requisition_number",
        "requisition__vacancy_title",
    )
    date_hierarchy = "date_received"
    fieldsets = (
        (
            "Candidate",
            {
                "fields": (
                    "requisition",
                    "first_name",
                    "last_name",
                    "gender",
                    "phone_number",
                    "email",
                    "national_id",
                    "address",
                )
            },
        ),
        (
            "Application Channel",
            {
                "fields": (
                    "application_source",
                    "date_received",
                    "online_profile_url",
                    "cv_file",
                    "application_form_file",
                )
            },
        ),
        (
            "Screening",
            {
                "fields": (
                    "highest_qualification",
                    "years_experience",
                    "current_employer",
                    "expected_salary",
                    "screening_score",
                    "police_clearance_no",
                    "background_check_status",
                    "medical_check_status",
                    "reference_check_status",
                    "status",
                    "notes",
                )
            },
        ),
    )


@admin.register(models.RecruitmentInterview)
class RecruitmentInterviewAdmin(admin.ModelAdmin):
    list_display = ("application", "interview_type", "scheduled_at", "interviewer", "score", "recommendation", "status")
    list_filter = ("interview_type", "recommendation", "status", "scheduled_at")
    search_fields = ("application__first_name", "application__last_name", "venue_or_link", "interviewer__first_name", "interviewer__last_name")
    date_hierarchy = "scheduled_at"


@admin.register(models.JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = ("application", "offered_position", "offer_date", "expected_start_date", "salary_offer", "contract_type", "status")
    list_filter = ("status", "contract_type", "offer_date")
    search_fields = ("application__first_name", "application__last_name", "offered_position__position_title")
    date_hierarchy = "offer_date"


@admin.register(models.Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "site", "schedule", "shift", "date", "time_in", "time_out", "status", "capture_source", "device_id", "geofence_distance_meters")
    list_filter = ("status", "capture_source", "date", "site")
    search_fields = ("employee__first_name", "employee__last_name", "employee__work_card_uid", "device_id", "site__site_name", "schedule__site__site_name")
    date_hierarchy = "date"


@admin.register(models.AttendanceDevice)
class AttendanceDeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "name", "assigned_site", "assigned_supervisor", "is_active")
    list_filter = ("is_active", "assigned_site")
    search_fields = ("device_id", "name", "assigned_site__site_name", "assigned_supervisor__first_name", "assigned_supervisor__last_name")


@admin.register(models.AttendanceDeviceEvent)
class AttendanceDeviceEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_timestamp",
        "device_identifier",
        "card_uid",
        "employee",
        "site",
        "event_type",
        "status",
        "geofence_distance_meters",
        "message",
    )
    list_filter = ("status", "event_type", "site", "event_timestamp")
    search_fields = ("device_identifier", "card_uid", "employee__first_name", "employee__last_name", "site__site_name", "message")
    date_hierarchy = "event_timestamp"


@admin.register(models.Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "days", "approval_status")
    list_filter = ("leave_type", "approval_status")
    search_fields = ("employee__first_name", "employee__last_name", "reason")
    date_hierarchy = "start_date"


@admin.register(models.DisciplinaryAction)
class DisciplinaryActionAdmin(admin.ModelAdmin):
    list_display = ("employee", "action_type", "action_date", "penalty", "status")
    list_filter = ("action_type", "status")
    search_fields = ("employee__first_name", "employee__last_name", "description", "penalty")
    date_hierarchy = "action_date"


@admin.register(models.PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ("employee", "eval_date", "rating", "evaluated_by")
    list_filter = ("rating",)
    search_fields = ("employee__first_name", "employee__last_name", "comments")
    date_hierarchy = "eval_date"


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "doc_type", "issue_date", "expiry_date")
    list_filter = ("doc_type",)
    search_fields = ("employee__first_name", "employee__last_name", "doc_type")


@admin.register(models.Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "pay_period_start",
        "pay_period_end",
        "attendance_days",
        "basic_hours",
        "overtime_hours",
        "gross_pay",
        "nssf_employee",
        "nssf_employer",
        "total_deductions",
        "net_salary",
        "status",
    )
    list_filter = ("status", "payment_method")
    search_fields = ("employee__first_name", "employee__last_name")
    date_hierarchy = "pay_period_start"


@admin.register(models.Advance)
class AdvanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "request_date", "amount_requested", "approval_status", "repayment_status")
    list_filter = ("approval_status", "repayment_status")
    search_fields = ("employee__first_name", "employee__last_name", "purpose")
    date_hierarchy = "request_date"


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "client",
        "site",
        "billing_month",
        "guard_count",
        "subtotal_amount",
        "vat_amount",
        "total_amount",
        "balance_amount",
        "status",
    )
    list_filter = ("status", "client", "site", "billing_month")
    search_fields = ("invoice_number", "client__client_name")
    date_hierarchy = "invoice_date"


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_date", "invoice", "employee", "amount", "payment_method", "transaction_ref")
    list_filter = ("payment_method",)
    search_fields = ("transaction_ref", "invoice__invoice_number", "employee__first_name", "employee__last_name")
    date_hierarchy = "payment_date"


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("account_code", "account_name", "account_type", "parent_account", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("account_code", "account_name")


class JournalLineInline(admin.TabularInline):
    model = models.JournalLine
    extra = 0


@admin.register(models.JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_date", "reference", "source_module", "total_debit", "total_credit", "status")
    list_filter = ("status", "source_module", "entry_date")
    search_fields = ("reference", "description")
    date_hierarchy = "entry_date"
    inlines = [JournalLineInline]


@admin.register(models.JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ("journal_entry", "account", "debit", "credit", "description")
    list_filter = ("account__account_type", "account")
    search_fields = ("journal_entry__reference", "account__account_code", "account__account_name", "description")


@admin.register(models.Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("year", "department", "category", "allocated_amount", "spent_amount", "remaining_amount")
    list_filter = ("year", "department")
    search_fields = ("category",)


@admin.register(models.Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "category", "amount", "approved_by", "receipt_no")
    list_filter = ("category",)
    search_fields = ("category", "description", "receipt_no")
    date_hierarchy = "expense_date"
