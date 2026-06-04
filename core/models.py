import re
import uuid
from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class StatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    PAID = "paid", "Paid"
    UNPAID = "unpaid", "Unpaid"
    CLOSED = "closed", "Closed"


class DepartmentChoices(models.TextChoices):
    OPERATIONS = "operations", "Operations"
    HUMAN_RESOURCE = "human_resource", "Human Resource"
    FINANCE = "finance", "Finance"
    ADMIN = "admin", "Admin"


phone_number_validator = RegexValidator(
    regex=r"^\+?\d{7,15}$",
    message="Enter a valid phone number using digits only, optionally starting with +.",
)


def validate_non_negative_fields(instance, field_names):
    errors = {}
    for field_name in field_names:
        value = getattr(instance, field_name, None)
        if value is not None and value < 0:
            errors[field_name] = "This value cannot be negative."
    if errors:
        raise ValidationError(errors)


class SubscriptionPlan(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user_limit = models.PositiveIntegerField(default=10)
    site_limit = models.PositiveIntegerField(default=25)
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["monthly_price", "name"]

    def __str__(self):
        return self.name


class TenantOrganization(TimeStampedModel):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True)
    primary_domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_tenant_organizations",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tenant_organizations",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    subscription_ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_subscription_active(self):
        now = timezone.now()
        if self.status in {self.Status.ACTIVE, self.Status.TRIALING}:
            return not self.subscription_ends_at or self.subscription_ends_at >= now
        return False


class TenantMembership(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    organization = models.ForeignKey(TenantOrganization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization__name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_tenant_membership"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization}"


class Client(TimeStampedModel):
    client_name = models.CharField(max_length=150, unique=True)
    contact_person = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30, validators=[phone_number_validator])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    contract_start_date = models.DateField()
    contract_end_date = models.DateField(null=True, blank=True)
    contract_status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )

    class Meta:
        ordering = ["client_name"]

    def __str__(self):
        return self.client_name

    def clean(self):
        super().clean()
        if self.contract_end_date and self.contract_end_date < self.contract_start_date:
            raise ValidationError({"contract_end_date": "Contract end date cannot be before start date."})
        duplicates = Client.objects.filter(client_name__iexact=self.client_name.strip())
        if self.pk:
            duplicates = duplicates.exclude(pk=self.pk)
        if duplicates.exists():
            raise ValidationError({"client_name": "A client with this name already exists."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Site(TimeStampedModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="sites")
    site_code = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    site_name = models.CharField(max_length=150)
    site_address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80, blank=True)
    security_level = models.CharField(max_length=50, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude for geofenced attendance capture.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude for geofenced attendance capture.",
    )
    geofence_radius_meters = models.PositiveIntegerField(
        default=150,
        help_text="Maximum distance from this site where IoT attendance can be captured.",
    )
    required_guards_per_shift = models.PositiveIntegerField(
        default=0,
        help_text="Contracted guard requirement per shift. Use 0 when not configured.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["client__client_name", "site_code", "site_name"]
        unique_together = ("client", "site_name")

    @staticmethod
    def client_code_prefix(client_name):
        words = re.findall(r"[A-Za-z0-9]+", client_name.upper())
        if not words:
            return "CLNT"
        if len(words) == 1:
            return words[0][:4].ljust(4, "X")
        return "".join(word[0] for word in words)[:4].ljust(4, "X")

    @classmethod
    def next_site_code(cls):
        existing_codes = cls.objects.filter(site_code__regex=r"^S\d+$").values_list("site_code", flat=True)
        next_number = 1
        for code in existing_codes:
            try:
                next_number = max(next_number, int(code[1:]) + 1)
            except (TypeError, ValueError):
                continue
        return f"S{next_number:03d}"

    def save(self, *args, **kwargs):
        if not self.site_code and self.client_id:
            self.site_code = self.next_site_code()
        super().save(*args, **kwargs)

    def __str__(self):
        code = self.site_code or "Uncoded"
        return f"{code} - {self.site_name}"

    def distance_to_meters(self, latitude, longitude):
        if self.latitude is None or self.longitude is None or latitude is None or longitude is None:
            return None
        site_lat = radians(float(self.latitude))
        site_lng = radians(float(self.longitude))
        point_lat = radians(float(latitude))
        point_lng = radians(float(longitude))
        delta_lat = point_lat - site_lat
        delta_lng = point_lng - site_lng
        haversine = sin(delta_lat / 2) ** 2 + cos(site_lat) * cos(point_lat) * sin(delta_lng / 2) ** 2
        return 6371000 * 2 * atan2(sqrt(haversine), sqrt(1 - haversine))

    def is_within_geofence(self, latitude, longitude):
        distance = self.distance_to_meters(latitude, longitude)
        if distance is None:
            return False, None
        return distance <= self.geofence_radius_meters, distance


class Contract(TimeStampedModel):
    class ContractType(models.TextChoices):
        FIXED_TERM = "fixed_term", "Fixed Term"
        RENEWABLE = "renewable", "Renewable"
        FRAMEWORK = "framework", "Framework Contract"
        ONE_TIME = "one_time", "One-Time Service"

    class ServiceType(models.TextChoices):
        MANNED_GUARDING = "Manned Guarding", "Manned Guarding"
        SITE_SUPERVISION = "Site Supervision", "Site Supervision"
        INCIDENT_MANAGEMENT = "Incident Management", "Incident Management"
        WORKFORCE_CONTROL = "Workforce Control", "Workforce Control"
        OTHERS = "Others", "Others"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMI_ANNUAL = "semi_annual", "Semi-Annual"
        ANNUALLY = "annually", "Annually"
        ONE_TIME = "one_time", "One Time"

    class PaymentTerm(models.TextChoices):
        NET_30 = "net_30", "Net 30 Days"
        NET_60 = "net_60", "Net 60 Days"
        ADVANCE = "advance", "Advance Payment"
        CUSTOM = "custom", "Custom"

    class ShiftPattern(models.TextChoices):
        EIGHT_HOURS = "8_hours", "8 Hours"
        TWELVE_HOURS = "12_hours", "12 Hours"
        TWENTY_FOUR_HOURS = "24_hours", "24 Hours"
        CUSTOM = "custom", "Custom"

    class ArmingStatus(models.TextChoices):
        UNARMED = "unarmed", "Unarmed"
        ARMED = "armed", "Armed"
        MIXED = "mixed", "Mixed"

    class UniformRequirement(models.TextChoices):
        COMPANY = "company", "Company Uniform"
        CLIENT = "client", "Client Uniform"
        BOTH = "both", "Client and Company Uniform"
        CUSTOM = "custom", "Custom"

    class Currency(models.TextChoices):
        UGX = "UGX", "UGX"
        USD = "USD", "USD"
        KES = "KES", "KES"
        TZS = "TZS", "TZS"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="contracts")
    deployment_site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )
    contract_manager = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_contracts",
    )
    contract_number = models.CharField(max_length=80, unique=True)
    contract_title = models.CharField(max_length=180, blank=True)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.FIXED_TERM)
    service_type = models.CharField(
        max_length=120,
        choices=ServiceType.choices,
        default=ServiceType.MANNED_GUARDING,
    )
    client_representative = models.CharField(max_length=150, blank=True)
    client_representative_title = models.CharField(max_length=120, blank=True)
    client_representative_email = models.EmailField(blank=True)
    client_representative_phone = models.CharField(max_length=30, blank=True, validators=[phone_number_validator])
    company_representative = models.CharField(max_length=150, blank=True)
    company_representative_title = models.CharField(max_length=120, blank=True)
    signed_date = models.DateField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    billing_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contract_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monthly_contract_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    annual_contract_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.UGX)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    payment_terms = models.CharField(max_length=20, choices=PaymentTerm.choices, default=PaymentTerm.NET_30)
    payment_terms_days = models.PositiveIntegerField(default=30)
    payment_instructions = models.TextField(blank=True)
    vat_applicable = models.BooleanField(default=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.18"))
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    service_scope = models.TextField(blank=True)
    service_location = models.CharField(max_length=180, blank=True)
    service_hours = models.CharField(max_length=120, blank=True)
    response_time_sla = models.CharField("Response time SLA", max_length=120, blank=True)
    incident_escalation_time = models.CharField(max_length=120, blank=True)
    patrol_frequency = models.CharField(max_length=120, blank=True)
    supervision_frequency = models.CharField(max_length=120, blank=True)
    guard_training_requirements = models.TextField(blank=True)
    day_guards_required = models.PositiveIntegerField(default=0)
    night_guards_required = models.PositiveIntegerField(default=0)
    supervisors_required = models.PositiveIntegerField(default=0)
    shift_pattern = models.CharField(max_length=20, choices=ShiftPattern.choices, blank=True)
    arming_status = models.CharField(max_length=20, choices=ArmingStatus.choices, default=ArmingStatus.UNARMED)
    patrol_required = models.BooleanField(default=False)
    radio_required = models.BooleanField(default=False)
    torch_required = models.BooleanField(default=False)
    metal_detector_required = models.BooleanField(default=False)
    vehicle_required = models.BooleanField(default=False)
    uniform_requirement = models.CharField(
        max_length=20,
        choices=UniformRequirement.choices,
        default=UniformRequirement.COMPANY,
    )
    client_obligations = models.TextField(blank=True)
    company_obligations = models.TextField(blank=True)
    confidentiality_clause = models.TextField(blank=True)
    liability_limit = models.CharField(max_length=180, blank=True)
    termination_notice_days = models.PositiveIntegerField(default=30)
    renewal_date = models.DateField(null=True, blank=True)
    renewal_reminder_days = models.PositiveIntegerField(default=60)
    renewal_terms = models.TextField(blank=True)
    governing_law = models.CharField(max_length=120, blank=True, default="Uganda")
    special_conditions = models.TextField(blank=True)
    late_payment_penalty = models.CharField(max_length=180, blank=True)
    service_breach_penalty = models.CharField(max_length=180, blank=True)
    signed_contract = models.FileField(upload_to="contract_documents/signed/", blank=True)
    amendment_document = models.FileField(upload_to="contract_documents/amendments/", blank=True)
    renewal_document = models.FileField(upload_to="contract_documents/renewals/", blank=True)
    dog_count = models.PositiveIntegerField(default=0)
    dog_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metal_detector_count = models.PositiveIntegerField(default=0)
    metal_detector_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    walk_through_detector_count = models.PositiveIntegerField(default=0)
    walk_through_detector_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    panic_baton_count = models.PositiveIntegerField(default=0)
    panic_baton_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    handcuffs_count = models.PositiveIntegerField(default=0)
    handcuffs_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    terms = models.TextField(blank=True)

    class Meta:
        ordering = ["client__client_name", "-start_date", "contract_number"]

    def __str__(self):
        return f"{self.contract_number} - {self.client}"

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "Contract end date cannot be before start date."})
        validate_non_negative_fields(
            self,
            (
                "billing_rate",
                "contract_value",
                "monthly_contract_value",
                "annual_contract_value",
                "vat_rate",
                "dog_rate",
                "metal_detector_rate",
                "walk_through_detector_rate",
                "panic_baton_rate",
                "handcuffs_rate",
            ),
        )

    @property
    def required_guards(self):
        configured_total = self.day_guards_required + self.night_guards_required + self.supervisors_required
        if configured_total:
            return configured_total
        return sum(
            requirement.required_guards
            for requirement in self.site_requirements.filter(status=StatusChoices.ACTIVE)
        )

    @property
    def contract_duration_days(self):
        if not self.start_date or not self.end_date:
            return None
        return max((self.end_date - self.start_date).days + 1, 0)

    @property
    def contract_duration_months(self):
        duration_days = self.contract_duration_days
        if duration_days is None:
            return None
        return round(duration_days / 30.4375, 1)

    @property
    def remaining_days(self):
        if not self.end_date:
            return None
        return max((self.end_date - timezone.localdate()).days, 0)

    @property
    def progress_percent(self):
        duration_days = self.contract_duration_days
        if not duration_days:
            return 0
        elapsed_days = (timezone.localdate() - self.start_date).days
        return min(max(round((elapsed_days / duration_days) * 100), 0), 100)

    @property
    def vat_amount(self):
        if not self.vat_applicable:
            return Decimal("0.00")
        base_amount = self.contract_value or self.annual_contract_value or self.monthly_contract_value
        return (base_amount * self.vat_rate).quantize(Decimal("0.01"))

    @property
    def total_contract_value_with_vat(self):
        base_amount = self.contract_value or self.annual_contract_value or self.monthly_contract_value
        return (base_amount + self.vat_amount).quantize(Decimal("0.01"))

    @property
    def other_deliverables(self):
        items = [
            ("Dogs", self.dog_count, self.dog_rate),
            ("Metal detectors", self.metal_detector_count, self.metal_detector_rate),
            ("Walk through detectors", self.walk_through_detector_count, self.walk_through_detector_rate),
            ("Panic batons", self.panic_baton_count, self.panic_baton_rate),
            ("Handcuffs", self.handcuffs_count, self.handcuffs_rate),
        ]
        deliverables = [
            f"{label}: {count} @ {rate}"
            for label, count, rate in items
            if count
        ]
        return ", ".join(deliverables) if deliverables else "-"


class ContractSiteRequirement(TimeStampedModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="site_requirements")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="contract_requirements")
    shift = models.ForeignKey("Shift", on_delete=models.SET_NULL, null=True, blank=True, related_name="contract_requirements")
    required_guards = models.PositiveIntegerField(default=1)
    rate_per_guard = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Leave 0 to use the parent contract billing rate.",
    )
    gun_count = models.PositiveIntegerField(default=0)
    gun_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    radio_count = models.PositiveIntegerField(default=0)
    radio_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metal_detector_count = models.PositiveIntegerField(default=0)
    metal_detector_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    walk_through_machine_count = models.PositiveIntegerField(default=0)
    walk_through_machine_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dog_count = models.PositiveIntegerField(default=0)
    dog_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    panic_baton_count = models.PositiveIntegerField(default=0)
    panic_baton_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    handcuffs_count = models.PositiveIntegerField(default=0)
    handcuffs_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["site__site_name", "shift__start_time", "start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "site", "shift", "start_date"],
                name="unique_contract_site_shift_start",
            )
        ]

    def __str__(self):
        shift = self.shift or "Any shift"
        return f"{self.site} - {shift}: {self.required_guards}"

    @property
    def effective_guard_rate(self):
        return self.rate_per_guard or self.contract.billing_rate

    @property
    def billing_rate(self):
        return self.effective_guard_rate

    @property
    def billable_total(self):
        return (
            (Decimal(self.required_guards) * self.effective_guard_rate)
            + (Decimal(self.gun_count) * self.gun_rate)
            + (Decimal(self.radio_count) * self.radio_rate)
            + (Decimal(self.metal_detector_count) * self.metal_detector_rate)
            + (Decimal(self.walk_through_machine_count) * self.walk_through_machine_rate)
            + (Decimal(self.dog_count) * self.dog_rate)
            + (Decimal(self.panic_baton_count) * self.panic_baton_rate)
            + (Decimal(self.handcuffs_count) * self.handcuffs_rate)
        ).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        if not self.rate_per_guard and self.contract_id:
            self.rate_per_guard = self.contract.billing_rate
        super().save(*args, **kwargs)


class Role(TimeStampedModel):
    role_name = models.CharField(max_length=80, unique=True)
    department = models.CharField(max_length=30, choices=DepartmentChoices.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["department", "role_name"]

    def __str__(self):
        return self.role_name


class Position(TimeStampedModel):
    position_title = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=30, choices=DepartmentChoices.choices)
    grade_level = models.CharField(max_length=30, blank=True)
    salary_range_min = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salary_range_max = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["department", "position_title"]

    def __str__(self):
        return self.position_title


class Employee(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=30, validators=[phone_number_validator])
    email = models.EmailField(unique=True)
    passport_photo = models.FileField(upload_to="employee_passport_photos/", blank=True)
    bank_account = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    national_id = models.CharField(max_length=80, unique=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="employees")
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees"
    )
    hire_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )
    company_number = models.CharField(max_length=80, unique=True, null=True, blank=True)
    work_card_uid = models.CharField(max_length=120, unique=True, null=True, blank=True)
    nssf_number = models.CharField("NSSF number", max_length=80, unique=True, null=True, blank=True)
    uniform_size = models.CharField(max_length=30, blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    next_of_keen = models.CharField(max_length=150, blank=True)
    next_of_keen_contact = models.CharField(max_length=150, blank=True, validators=[phone_number_validator])
    training_level = models.CharField(max_length=80, blank=True)
    assigned_zone = models.CharField(max_length=120, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    authority_level = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name

    def clean(self):
        super().clean()
        duplicates = Employee.objects.filter(
            first_name__iexact=self.first_name.strip(),
            last_name__iexact=self.last_name.strip(),
            phone_number=self.phone_number,
        )
        if self.pk:
            duplicates = duplicates.exclude(pk=self.pk)
        if duplicates.exists():
            raise ValidationError("A guard with the same name and phone number already exists.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Zone(TimeStampedModel):
    zone_code = models.CharField(max_length=30, unique=True)
    zone_name = models.CharField(max_length=120, unique=True)
    supervisor = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="supervised_zones")
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )

    class Meta:
        ordering = ["zone_name"]

    def __str__(self):
        return f"{self.zone_code} - {self.zone_name}"


class ZoneEmployeeAllocation(TimeStampedModel):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="employee_allocations")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="zone_allocations")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_zone_allocations",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["zone", "employee__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                condition=Q(status=StatusChoices.ACTIVE, end_date__isnull=True),
                name="unique_active_employee_zone",
            )
        ]

    def __str__(self):
        return f"{self.employee} -> {self.zone}"


class ZoneSiteAllocation(TimeStampedModel):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="site_allocations")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="zone_allocations")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_zone_allocations",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["zone", "site__site_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["site"],
                condition=Q(status=StatusChoices.ACTIVE, end_date__isnull=True),
                name="unique_active_site_zone",
            )
        ]

    def __str__(self):
        return f"{self.site} -> {self.zone}"


class Shift(TimeStampedModel):
    UGANDA_BASIC_HOURS_PER_DAY = Decimal("8.00")
    UGANDA_NORMAL_DAY_OVERTIME_MULTIPLIER = Decimal("1.50")
    UGANDA_PUBLIC_HOLIDAY_OVERTIME_MULTIPLIER = Decimal("2.00")

    shift_name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=10, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["start_time", "shift_name"]

    @property
    def duration_hours(self):
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        return (Decimal(end_minutes - start_minutes) / Decimal(60)).quantize(Decimal("0.01"))

    @property
    def basic_hours(self):
        return min(self.duration_hours, self.UGANDA_BASIC_HOURS_PER_DAY)

    @property
    def daily_overtime_hours(self):
        return max(self.duration_hours - self.UGANDA_BASIC_HOURS_PER_DAY, Decimal("0.00"))

    @property
    def normal_day_overtime_multiplier(self):
        return self.UGANDA_NORMAL_DAY_OVERTIME_MULTIPLIER

    @property
    def public_holiday_overtime_multiplier(self):
        return self.UGANDA_PUBLIC_HOLIDAY_OVERTIME_MULTIPLIER

    def __str__(self):
        return self.shift_name


class Deployment(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="deployments")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="deployments")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="deployments")
    supervisor = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="supervised_deployments"
    )
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="deployments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )

    class Meta:
        ordering = ["-start_date"]

    @property
    def employee_number(self):
        return self.employee.company_number

    def __str__(self):
        return f"{self.employee} at {self.site}"

    def clean(self):
        super().clean()
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "Deployment end date cannot be before start date."})
        if not self.employee_id or not self.site_id or not self.start_date:
            return
        if self.status != StatusChoices.ACTIVE:
            return
        deployment_end = self.end_date or timezone.datetime.max.date()
        conflicts = Deployment.objects.filter(
            employee_id=self.employee_id,
            status=StatusChoices.ACTIVE,
            start_date__lte=deployment_end,
        ).filter(Q(end_date__gte=self.start_date) | Q(end_date__isnull=True))
        if self.pk:
            conflicts = conflicts.exclude(pk=self.pk)
        conflicts = conflicts.exclude(site_id=self.site_id)
        if conflicts.exists():
            raise ValidationError(
                {"site": "This guard already has an active overlapping deployment at another site."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class GuardSchedule(TimeStampedModel):
    class ScheduleStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"
        CANCELLED = "cancelled", "Cancelled"

    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="schedules")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="schedules")
    replacement_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_schedules",
    )
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="guard_schedules")
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="guard_schedules")
    shift_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=ScheduleStatus.choices, default=ScheduleStatus.SCHEDULED
    )
    replacement_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["shift_date", "shift__start_time", "employee__first_name"]
        unique_together = ("deployment", "shift_date")

    def __str__(self):
        return f"{self.employee} - {self.site} - {self.shift_date}"

    def required_guard_limit(self):
        if not self.site_id or not self.shift_id or not self.shift_date:
            return None
        requirement = (
            ContractSiteRequirement.objects.select_related("contract")
            .filter(
                site_id=self.site_id,
                status=StatusChoices.ACTIVE,
                contract__status=StatusChoices.ACTIVE,
                start_date__lte=self.shift_date,
            )
            .filter(Q(end_date__gte=self.shift_date) | Q(end_date__isnull=True))
            .filter(Q(contract__end_date__gte=self.shift_date) | Q(contract__end_date__isnull=True))
            .filter(Q(shift_id=self.shift_id) | Q(shift__isnull=True))
            .order_by("-shift_id", "-start_date")
            .first()
        )
        if requirement:
            return requirement.required_guards
        if self.site_id:
            return self.site.required_guards_per_shift
        return None

    def clean(self):
        super().clean()
        if self.deployment_id:
            if self.employee_id and self.employee_id != self.deployment.employee_id:
                raise ValidationError({"employee": "Schedule employee must match the deployment employee."})
            if self.site_id and self.site_id != self.deployment.site_id:
                raise ValidationError({"site": "Schedule site must match the deployment site."})
            if self.shift_id and self.shift_id != self.deployment.shift_id:
                raise ValidationError({"shift": "Schedule shift must match the deployment shift."})
            if self.shift_date and self.shift_date < self.deployment.start_date:
                raise ValidationError({"shift_date": "Schedule date cannot be before deployment start date."})
            if self.shift_date and self.deployment.end_date and self.shift_date > self.deployment.end_date:
                raise ValidationError({"shift_date": "Schedule date cannot be after deployment end date."})
        if self.status == self.ScheduleStatus.CANCELLED:
            return
        limit = self.required_guard_limit()
        if not limit:
            return
        schedules = GuardSchedule.objects.filter(
            site_id=self.site_id,
            shift_id=self.shift_id,
            shift_date=self.shift_date,
        ).exclude(status=self.ScheduleStatus.CANCELLED)
        if self.pk:
            schedules = schedules.exclude(pk=self.pk)
        if schedules.count() >= limit:
            raise ValidationError(
                {
                    "site": (
                        f"{self.site} already has the required {limit} guard(s) "
                        f"for {self.shift} on {self.shift_date}."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class RosterAttendance(TimeStampedModel):
    class ImportStatus(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        SKIPPED = "skipped", "Skipped"
        OFF = "off", "Off"

    class SourceFormat(models.TextChoices):
        SIMPLE = "simple", "Simple Excel"
        SARACEN = "saracen", "Saracen Excel"
        WIDE_MONTHLY = "wide_monthly", "Wide Monthly Excel"

    batch_reference = models.CharField(max_length=36, default=uuid.uuid4, db_index=True)
    file_name = models.CharField(max_length=255, blank=True)
    source_format = models.CharField(max_length=20, choices=SourceFormat.choices, default=SourceFormat.SIMPLE)
    source_row = models.PositiveIntegerField(default=0)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="roster_attendances")
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="roster_attendances")
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True, related_name="roster_attendances")
    shift_date = models.DateField(null=True, blank=True)
    schedule = models.ForeignKey(GuardSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="roster_attendances")
    duty_code = models.CharField(max_length=40, blank=True)
    import_status = models.CharField(max_length=20, choices=ImportStatus.choices, default=ImportStatus.CREATED)
    message = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="roster_upload_rows")

    class Meta:
        ordering = ["-created_at", "shift_date", "site__site_name", "employee__first_name"]
        verbose_name = "Roster attendance"
        verbose_name_plural = "Roster attendances"

    def __str__(self):
        return f"{self.shift_date or 'No date'} - {self.employee or 'Unknown guard'} - {self.get_import_status_display()}"


class Incident(TimeStampedModel):
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="incidents")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="incidents")
    incident_type = models.CharField(max_length=100)
    description = models.TextField()
    incident_date = models.DateTimeField()
    location = models.CharField(max_length=150)
    severity_level = models.CharField(max_length=50)
    reported_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="reported_incidents"
    )
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    class Meta:
        ordering = ["-incident_date"]

    def __str__(self):
        return f"{self.incident_type} - {self.incident_date:%Y-%m-%d}"


class PatrolLog(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="patrol_logs")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="patrol_logs")
    patrol_time = models.DateTimeField()
    patrol_route = models.CharField(max_length=200)
    observations = models.TextField(blank=True)
    photos = models.FileField(upload_to="patrol_photos/", blank=True)

    class Meta:
        ordering = ["-patrol_time"]

    def __str__(self):
        return f"{self.employee} - {self.patrol_time:%Y-%m-%d %H:%M}"


class Asset(TimeStampedModel):
    asset_name = models.CharField(max_length=150)
    asset_type = models.CharField(max_length=80)
    serial_number = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=80, blank=True)
    assigned_to = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    issue_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["asset_name"]

    def __str__(self):
        return f"{self.asset_name} ({self.serial_number})"


class Training(TimeStampedModel):
    class TrainingType(models.TextChoices):
        INDUCTION = "induction", "Induction"
        REFRESHER = "refresher", "Refresher"
        COMPLIANCE = "compliance", "Compliance"
        FIRE_SAFETY = "fire_safety", "Fire Safety"
        FIRST_AID = "first_aid", "First Aid"
        CUSTOMER_CARE = "customer_care", "Customer Care"
        SUPERVISORY = "supervisory", "Supervisory"
        FIREARMS = "firearms", "Firearms"
        RADIO_COMMUNICATION = "radio_communication", "Radio Communication"
        SITE_PROCEDURES = "site_procedures", "Site Procedures"

    class TrainingResult(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="trainings")
    training_name = models.CharField(max_length=150)
    course_code = models.CharField(max_length=40, blank=True)
    training_type = models.CharField(max_length=40, choices=TrainingType.choices, default=TrainingType.INDUCTION)
    training_objective = models.TextField(blank=True)
    provider = models.CharField(max_length=150, blank=True)
    trainer_name = models.CharField(max_length=150, blank=True)
    trainer_contact = models.CharField(max_length=80, blank=True)
    venue = models.CharField(max_length=150, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    duration_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    budgeted_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    training_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pass_mark = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    result = models.CharField(max_length=30, choices=TrainingResult.choices, default=TrainingResult.SCHEDULED)
    certificate_no = models.CharField(max_length=100, blank=True)
    certificate_file = models.FileField(upload_to="training_certificates/", blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    next_refresh_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_trainings"
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    action_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date", "training_name"]

    @property
    def is_certificate_current(self):
        return not self.expiry_date or self.expiry_date >= timezone.localdate()

    @property
    def final_score(self):
        if self.score is None:
            return ""
        return f"{self.score}%"

    def __str__(self):
        return f"{self.training_name} - {self.employee}"


class RecruitmentRequisition(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        CONTRACT = "contract", "Contract"
        CASUAL = "casual", "Casual"
        INTERNSHIP = "internship", "Internship"

    class RequisitionStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        SHORTLISTING = "shortlisting", "Shortlisting"
        INTERVIEWING = "interviewing", "Interviewing"
        OFFERING = "offering", "Offering"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    requisition_number = models.CharField(max_length=80, unique=True)
    vacancy_title = models.CharField(max_length=150)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name="requisitions")
    department = models.CharField(max_length=30, choices=DepartmentChoices.choices)
    requested_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_requisitions"
    )
    number_of_openings = models.PositiveIntegerField(default=1)
    employment_type = models.CharField(max_length=30, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    work_location = models.CharField(max_length=150, blank=True)
    opening_date = models.DateField(default=timezone.localdate)
    closing_date = models.DateField(null=True, blank=True)
    salary_budget_min = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salary_budget_max = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recruitment_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_recruitment_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    minimum_qualification = models.CharField(max_length=180, blank=True)
    experience_required = models.CharField(max_length=150, blank=True)
    job_description = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=RequisitionStatus.choices, default=RequisitionStatus.DRAFT)

    class Meta:
        ordering = ["-opening_date", "requisition_number"]
        verbose_name = "Recruitment requisition"
        verbose_name_plural = "Recruitment requisitions"

    @property
    def applications_count(self):
        return self.applications.count()

    @property
    def hired_count(self):
        return self.applications.filter(status=RecruitmentApplication.ApplicationStatus.HIRED).count()

    def __str__(self):
        return f"{self.requisition_number} - {self.vacancy_title}"


class RecruitmentApplication(TimeStampedModel):
    class ApplicationSource(models.TextChoices):
        PHYSICAL = "physical", "Physical Walk-in"
        ONLINE = "online", "Online Application"
        REFERRAL = "referral", "Employee Referral"
        AGENCY = "agency", "Recruitment Agency"
        JOB_BOARD = "job_board", "Job Board"

    class ApplicationStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        SCREENING = "screening", "Screening"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        BACKGROUND_CHECK = "background_check", "Background Check"
        OFFERED = "offered", "Offered"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    requisition = models.ForeignKey(RecruitmentRequisition, on_delete=models.CASCADE, related_name="applications")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    gender = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=30, validators=[phone_number_validator])
    email = models.EmailField(blank=True)
    national_id = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    application_source = models.CharField(
        max_length=30, choices=ApplicationSource.choices, default=ApplicationSource.PHYSICAL
    )
    date_received = models.DateField(default=timezone.localdate)
    online_profile_url = models.URLField(blank=True)
    cv_file = models.FileField(upload_to="recruitment_cvs/", blank=True)
    application_form_file = models.FileField(upload_to="recruitment_forms/", blank=True)
    highest_qualification = models.CharField(max_length=180, blank=True)
    years_experience = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    current_employer = models.CharField(max_length=150, blank=True)
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    screening_score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    police_clearance_no = models.CharField(max_length=100, blank=True)
    background_check_status = models.CharField(max_length=80, blank=True)
    medical_check_status = models.CharField(max_length=80, blank=True)
    reference_check_status = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=30, choices=ApplicationStatus.choices, default=ApplicationStatus.RECEIVED)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_received", "last_name", "first_name"]
        verbose_name = "Recruitment application"
        verbose_name_plural = "Recruitment applications"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} - {self.requisition.vacancy_title}"


class RecruitmentInterview(TimeStampedModel):
    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone"
        ONLINE = "online", "Online"
        PHYSICAL = "physical", "Physical"
        PANEL = "panel", "Panel"
        PRACTICAL = "practical", "Practical Assessment"

    class InterviewRecommendation(models.TextChoices):
        PENDING = "pending", "Pending"
        RECOMMENDED = "recommended", "Recommended"
        HOLD = "hold", "Hold"
        NOT_RECOMMENDED = "not_recommended", "Not Recommended"

    application = models.ForeignKey(RecruitmentApplication, on_delete=models.CASCADE, related_name="interviews")
    interview_type = models.CharField(max_length=30, choices=InterviewType.choices, default=InterviewType.PHYSICAL)
    scheduled_at = models.DateTimeField()
    venue_or_link = models.CharField(max_length=220, blank=True)
    interviewer = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="recruitment_interviews"
    )
    score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    recommendation = models.CharField(
        max_length=30,
        choices=InterviewRecommendation.choices,
        default=InterviewRecommendation.PENDING,
    )
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    class Meta:
        ordering = ["-scheduled_at", "application"]
        verbose_name = "Recruitment interview"
        verbose_name_plural = "Recruitment interviews"

    def __str__(self):
        return f"{self.application.full_name} - {self.get_interview_type_display()}"


class JobOffer(TimeStampedModel):
    class OfferStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    application = models.OneToOneField(RecruitmentApplication, on_delete=models.CASCADE, related_name="job_offer")
    offered_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name="job_offers")
    offer_date = models.DateField(default=timezone.localdate)
    expected_start_date = models.DateField(null=True, blank=True)
    salary_offer = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contract_type = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=30, choices=OfferStatus.choices, default=OfferStatus.DRAFT)
    accepted_date = models.DateField(null=True, blank=True)
    offer_letter = models.FileField(upload_to="offer_letters/", blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-offer_date", "application"]
        verbose_name = "Job offer"
        verbose_name_plural = "Job offers"

    def __str__(self):
        return f"Offer to {self.application.full_name}"


class Attendance(TimeStampedModel):
    class CaptureSource(models.TextChoices):
        MANUAL = "manual", "Manual"
        IOT = "iot", "IoT Device"
        IMPORT = "import", "Imported"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    schedule = models.OneToOneField(
        GuardSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance",
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=30, default="Present")
    capture_source = models.CharField(max_length=20, choices=CaptureSource.choices, default=CaptureSource.MANUAL)
    card_uid = models.CharField(max_length=120, blank=True)
    device_id = models.CharField(max_length=120, blank=True)
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="captured_attendances",
    )
    captured_at = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geofence_distance_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ("employee", "date", "shift", "site")

    def __str__(self):
        return f"{self.employee} - {self.date}"

    def clean(self):
        super().clean()
        if self.schedule_id:
            if self.employee_id and self.employee_id != self.schedule.employee_id:
                raise ValidationError({"employee": "Attendance employee must match the schedule employee."})
            if self.site_id and self.site_id != self.schedule.site_id:
                raise ValidationError({"site": "Attendance site must match the schedule site."})
            if self.shift_id and self.shift_id != self.schedule.shift_id:
                raise ValidationError({"shift": "Attendance shift must match the schedule shift."})
            if self.date and self.date != self.schedule.shift_date:
                raise ValidationError({"date": "Attendance date must match the schedule date."})
            deployment = self.schedule.deployment
            if self.date and self.date < deployment.start_date:
                raise ValidationError({"date": "Attendance date cannot be before deployment start date."})
            if self.date and deployment.end_date and self.date > deployment.end_date:
                raise ValidationError({"date": "Attendance date cannot be after deployment end date."})
        elif self.employee_id and self.site_id and self.shift_id and self.date:
            deployment_exists = Deployment.objects.filter(
                employee_id=self.employee_id,
                site_id=self.site_id,
                shift_id=self.shift_id,
                status=StatusChoices.ACTIVE,
                start_date__lte=self.date,
            ).filter(Q(end_date__gte=self.date) | Q(end_date__isnull=True)).exists()
            if not deployment_exists:
                raise ValidationError({"date": "Attendance must be linked to an active deployment for this date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AttendanceDevice(TimeStampedModel):
    device_id = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=150)
    api_key = models.CharField(max_length=120, unique=True)
    assigned_site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_devices")
    assigned_supervisor = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_devices",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["device_id"]

    def __str__(self):
        return f"{self.device_id} - {self.name}"


class AttendanceDeviceEvent(TimeStampedModel):
    class EventType(models.TextChoices):
        CHECK_IN = "check_in", "Check In"
        CHECK_OUT = "check_out", "Check Out"

    class EventStatus(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    device = models.ForeignKey(
        AttendanceDevice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    device_identifier = models.CharField(max_length=120, blank=True)
    card_uid = models.CharField(max_length=120, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="device_events")
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_events")
    schedule = models.ForeignKey(
        GuardSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device_events",
    )
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device_events",
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.CHECK_IN)
    event_timestamp = models.DateTimeField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geofence_distance_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.REJECTED)
    message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-event_timestamp", "-created_at"]

    def __str__(self):
        return f"{self.device_identifier or self.device_id} {self.card_uid} {self.event_timestamp:%Y-%m-%d %H:%M}"


class Leave(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField()
    reason = models.TextField(blank=True)
    approval_status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_leaves"
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Leave request"
        verbose_name_plural = "Leave requests"

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"


class DisciplinaryAction(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="disciplinary_actions")
    action_type = models.CharField(max_length=100)
    description = models.TextField()
    action_date = models.DateField()
    penalty = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_disciplinary_actions",
    )

    class Meta:
        ordering = ["-action_date"]
        verbose_name = "Disciplinary action"
        verbose_name_plural = "Disciplinary actions"

    def __str__(self):
        return f"{self.action_type} - {self.employee}"


class PerformanceEvaluation(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="evaluations")
    eval_date = models.DateField()
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True)
    evaluated_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="evaluations_given"
    )

    class Meta:
        ordering = ["-eval_date"]
        verbose_name = "Performance evaluation"
        verbose_name_plural = "Performance evaluations"

    def __str__(self):
        return f"{self.employee} rating {self.rating}/5"


class Document(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=80)
    file_path = models.FileField(upload_to="employee_documents/")
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["employee", "doc_type"]
        verbose_name = "Employee document"
        verbose_name_plural = "Employee documents"

    def __str__(self):
        return f"{self.doc_type} - {self.employee}"


class Salary(TimeStampedModel):
    NSSF_EMPLOYEE_RATE = Decimal("0.05")
    NSSF_EMPLOYER_RATE = Decimal("0.10")

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="salaries")
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    attendance_days = models.PositiveIntegerField(default=0)
    basic_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nssf_employee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nssf_employer = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.UNPAID)

    class Meta:
        ordering = ["-pay_period_start", "employee"]
        verbose_name = "Salary"
        verbose_name_plural = "Salaries"
        constraints = [
            models.UniqueConstraint(fields=["employee", "pay_period_start"], name="unique_employee_pay_period"),
        ]

    def clean(self):
        super().clean()
        if self.pay_period_end and self.pay_period_start and self.pay_period_end < self.pay_period_start:
            raise ValidationError({"pay_period_end": "Pay period end cannot be before pay period start."})
        validate_non_negative_fields(
            self,
            (
                "basic_hours",
                "overtime_hours",
                "basic_salary",
                "allowances",
                "deductions",
                "advance_deduction",
                "advance_balance",
                "overtime_pay",
                "bonus",
                "gross_pay",
                "nssf_employee",
                "nssf_employer",
                "total_deductions",
                "net_salary",
            ),
        )

    def save(self, *args, **kwargs):
        self.gross_pay = self.basic_salary + self.allowances + self.overtime_pay + self.bonus
        self.nssf_employee = (self.gross_pay * self.NSSF_EMPLOYEE_RATE).quantize(Decimal("0.01"))
        self.nssf_employer = (self.gross_pay * self.NSSF_EMPLOYER_RATE).quantize(Decimal("0.01"))
        self.total_deductions = self.nssf_employee + self.deductions + self.advance_deduction
        self.net_salary = self.gross_pay - self.total_deductions
        self.full_clean()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                "gross_pay",
                "nssf_employee",
                "nssf_employer",
                "total_deductions",
                "net_salary",
            }
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.pay_period_start:%b %Y}"


class Advance(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="advances")
    request_date = models.DateField(default=timezone.localdate)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField(blank=True)
    approval_status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_advances"
    )
    disbursement_date = models.DateField(null=True, blank=True)
    repayment_status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )

    class Meta:
        ordering = ["-request_date"]

    def __str__(self):
        return f"{self.employee} advance {self.amount_requested}"


class Invoice(TimeStampedModel):
    VAT_RATE = Decimal("0.18")

    class BillingScope(models.TextChoices):
        SITE = "site", "One Site"
        MULTIPLE_SITES = "multiple_sites", "Selected Sites"
        CONTRACT = "contract", "All Contract Sites"

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="invoices")
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    selected_sites = models.ManyToManyField(Site, blank=True, related_name="multi_site_invoices")
    billing_scope = models.CharField(max_length=20, choices=BillingScope.choices, default=BillingScope.SITE)
    client_name = models.CharField(max_length=150, blank=True)
    client_address = models.TextField(blank=True)
    client_email = models.EmailField(blank=True)
    client_contact_person = models.CharField(max_length=150, blank=True)
    client_phone_number = models.CharField(max_length=30, blank=True)
    invoice_number = models.CharField(max_length=80, unique=True, blank=True)
    billing_month = models.DateField(null=True, blank=True)
    invoice_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    guard_count = models.PositiveIntegerField(default=0)
    rate_per_guard = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gun_count = models.PositiveIntegerField(default=0)
    gun_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    radio_count = models.PositiveIntegerField(default=0)
    radio_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metal_detector_count = models.PositiveIntegerField(default=0)
    metal_detector_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    walk_through_machine_count = models.PositiveIntegerField(default=0)
    walk_through_machine_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dog_count = models.PositiveIntegerField(default=0)
    dog_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=VAT_RATE)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.UNPAID)

    class Meta:
        ordering = ["-invoice_date", "invoice_number"]

    @classmethod
    def next_invoice_number(cls, invoice_date):
        prefix = f"INV-{invoice_date:%Y%m}"
        existing = cls.objects.filter(invoice_number__startswith=prefix).count() + 1
        return f"{prefix}-{existing:04d}"

    def resolved_guard_count(self):
        if self.guard_count:
            return self.guard_count
        summary = self.contract_billing_summary()
        if summary:
            return summary["guard_count"]
        if self.contract_id and self.site_id and self.billing_month:
            requirements = ContractSiteRequirement.objects.filter(
                contract=self.contract,
                site=self.site,
                status=StatusChoices.ACTIVE,
                start_date__lte=self.billing_month,
            ).filter(Q(end_date__gte=self.billing_month) | Q(end_date__isnull=True))
            guard_count = sum(requirement.required_guards for requirement in requirements)
            if guard_count:
                return guard_count
        if self.site_id and self.site.required_guards_per_shift:
            return self.site.required_guards_per_shift
        if self.contract_id:
            return self.contract.required_guards
        return 0

    def active_contract_requirements(self):
        if not self.contract_id or not self.billing_month:
            return ContractSiteRequirement.objects.none()
        requirements = ContractSiteRequirement.objects.select_related("contract", "site").filter(
            contract=self.contract,
            status=StatusChoices.ACTIVE,
            start_date__lte=self.billing_month,
        ).filter(Q(end_date__gte=self.billing_month) | Q(end_date__isnull=True))
        if self.billing_scope == self.BillingScope.SITE:
            if not self.site_id:
                return ContractSiteRequirement.objects.none()
            requirements = requirements.filter(site=self.site)
        elif self.billing_scope == self.BillingScope.MULTIPLE_SITES:
            if not self.pk:
                return ContractSiteRequirement.objects.none()
            selected_site_ids = self.selected_sites.values_list("id", flat=True)
            requirements = requirements.filter(site_id__in=selected_site_ids)
        return requirements

    def contract_billing_summary(self):
        requirements = list(self.active_contract_requirements())
        if not requirements:
            return None
        summary = {
            "guard_count": 0,
            "guard_rates": set(),
            "gun_count": 0,
            "gun_rates": set(),
            "radio_count": 0,
            "radio_rates": set(),
            "metal_detector_count": 0,
            "metal_detector_rates": set(),
            "walk_through_machine_count": 0,
            "walk_through_machine_rates": set(),
            "dog_count": 0,
            "dog_rates": set(),
            "subtotal": Decimal("0.00"),
        }
        for requirement in requirements:
            summary["guard_count"] += requirement.required_guards
            summary["guard_rates"].add(requirement.effective_guard_rate)
            summary["gun_count"] += requirement.gun_count
            summary["gun_rates"].add(requirement.gun_rate)
            summary["radio_count"] += requirement.radio_count
            summary["radio_rates"].add(requirement.radio_rate)
            summary["metal_detector_count"] += requirement.metal_detector_count
            summary["metal_detector_rates"].add(requirement.metal_detector_rate)
            summary["walk_through_machine_count"] += requirement.walk_through_machine_count
            summary["walk_through_machine_rates"].add(requirement.walk_through_machine_rate)
            summary["dog_count"] += requirement.dog_count
            summary["dog_rates"].add(requirement.dog_rate)
            summary["subtotal"] += requirement.billable_total
        summary["subtotal"] = summary["subtotal"].quantize(Decimal("0.01"))
        return summary

    @staticmethod
    def single_rate(rates):
        non_zero_rates = {rate for rate in rates if rate}
        if len(non_zero_rates) == 1:
            return non_zero_rates.pop()
        return Decimal("0.00")

    def sync_client_snapshot(self):
        if self.contract_id:
            self.client = self.contract.client
        if self.client_id:
            self.client_name = self.client.client_name
            self.client_address = self.client.address
            self.client_email = self.client.email
            self.client_contact_person = self.client.contact_person
            self.client_phone_number = self.client.phone_number

    def clean(self):
        super().clean()
        if self.due_date and self.invoice_date and self.due_date < self.invoice_date:
            raise ValidationError({"due_date": "Due date cannot be before invoice date."})
        if self.contract_id and self.client_id and self.contract.client_id != self.client_id:
            raise ValidationError({"client": "Invoice client must match the selected contract client."})
        if self.contract_id and self.site_id:
            if self.site.client_id != self.contract.client_id:
                raise ValidationError({"site": "Invoice site must belong to the contract client."})
            if not ContractSiteRequirement.objects.filter(contract=self.contract, site=self.site).exists():
                raise ValidationError({"site": "Invoice site must be part of the selected contract."})
        validate_non_negative_fields(
            self,
            (
                "rate_per_guard",
                "gun_rate",
                "radio_rate",
                "metal_detector_rate",
                "walk_through_machine_rate",
                "dog_rate",
                "subtotal_amount",
                "vat_rate",
                "vat_amount",
                "total_amount",
                "paid_amount",
                "balance_amount",
            ),
        )
        if self.total_amount is not None and self.paid_amount is not None and self.paid_amount > self.total_amount:
            raise ValidationError({"paid_amount": "Paid amount cannot exceed the invoice total."})

    def save(self, *args, **kwargs):
        self.sync_client_snapshot()
        if self.billing_scope in {self.BillingScope.CONTRACT, self.BillingScope.MULTIPLE_SITES}:
            self.site = None
        if not self.invoice_number:
            self.invoice_number = self.next_invoice_number(self.invoice_date)
        summary = self.contract_billing_summary()
        if summary:
            manual_items = (
                ("gun", self.gun_count, self.gun_rate),
                ("radio", self.radio_count, self.radio_rate),
                ("metal_detector", self.metal_detector_count, self.metal_detector_rate),
                ("walk_through_machine", self.walk_through_machine_count, self.walk_through_machine_rate),
                ("dog", self.dog_count, self.dog_rate),
            )
            for item_name, item_count, item_rate in manual_items:
                if item_count and item_rate and not summary[f"{item_name}_count"]:
                    summary[f"{item_name}_count"] += item_count
                    summary[f"{item_name}_rates"].add(item_rate)
                    summary["subtotal"] += (Decimal(item_count) * item_rate).quantize(Decimal("0.01"))
            self.guard_count = summary["guard_count"]
            self.rate_per_guard = self.single_rate(summary["guard_rates"])
            self.gun_count = summary["gun_count"]
            self.gun_rate = self.single_rate(summary["gun_rates"])
            self.radio_count = summary["radio_count"]
            self.radio_rate = self.single_rate(summary["radio_rates"])
            self.metal_detector_count = summary["metal_detector_count"]
            self.metal_detector_rate = self.single_rate(summary["metal_detector_rates"])
            self.walk_through_machine_count = summary["walk_through_machine_count"]
            self.walk_through_machine_rate = self.single_rate(summary["walk_through_machine_rates"])
            self.dog_count = summary["dog_count"]
            self.dog_rate = self.single_rate(summary["dog_rates"])
            self.subtotal_amount = summary["subtotal"]
            self.vat_amount = (self.subtotal_amount * self.vat_rate).quantize(Decimal("0.01"))
            self.total_amount = self.subtotal_amount + self.vat_amount
        else:
            if not self.guard_count:
                self.guard_count = self.resolved_guard_count()
            if not self.rate_per_guard and self.contract_id:
                self.rate_per_guard = self.contract.billing_rate
            computed_subtotal = (
                (Decimal(self.guard_count) * self.rate_per_guard)
                + (Decimal(self.gun_count) * self.gun_rate)
                + (Decimal(self.radio_count) * self.radio_rate)
                + (Decimal(self.metal_detector_count) * self.metal_detector_rate)
                + (Decimal(self.walk_through_machine_count) * self.walk_through_machine_rate)
                + (Decimal(self.dog_count) * self.dog_rate)
            ).quantize(Decimal("0.01"))
            if computed_subtotal:
                self.subtotal_amount = computed_subtotal
                self.vat_amount = (self.subtotal_amount * self.vat_rate).quantize(Decimal("0.01"))
                self.total_amount = self.subtotal_amount + self.vat_amount
            elif self.total_amount and not self.subtotal_amount:
                self.subtotal_amount = (self.total_amount / (Decimal("1.00") + self.vat_rate)).quantize(Decimal("0.01"))
                self.vat_amount = self.total_amount - self.subtotal_amount
            else:
                self.subtotal_amount = Decimal("0.00")
                self.vat_amount = Decimal("0.00")
                self.total_amount = Decimal("0.00")
        self.balance_amount = self.total_amount - self.paid_amount
        if self.balance_amount <= 0:
            self.status = StatusChoices.PAID
        else:
            self.status = StatusChoices.UNPAID
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number


class Payment(TimeStampedModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    payment_date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=80)
    transaction_ref = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        target = self.invoice or self.employee or "General"
        return f"{target} payment {self.amount}"


class Account(TimeStampedModel):
    class AccountType(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    account_code = models.CharField(max_length=20, unique=True)
    account_name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent_account = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_accounts"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["account_code"]

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"


class JournalEntry(TimeStampedModel):
    class EntryStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    entry_date = models.DateField(default=timezone.localdate)
    reference = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    source_module = models.CharField(max_length=50, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )
    status = models.CharField(max_length=20, choices=EntryStatus.choices, default=EntryStatus.POSTED)

    class Meta:
        ordering = ["-entry_date", "reference"]
        verbose_name = "Journal entry"
        verbose_name_plural = "Journal entries"

    @property
    def total_debit(self):
        return sum(line.debit for line in self.lines.all())

    @property
    def total_credit(self):
        return sum(line.credit for line in self.lines.all())

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def __str__(self):
        return self.reference


class JournalLine(TimeStampedModel):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["journal_entry__entry_date", "journal_entry__reference", "id"]
        verbose_name = "Journal line"
        verbose_name_plural = "Journal lines"

    def clean(self):
        super().clean()
        if self.debit and self.credit:
            from django.core.exceptions import ValidationError

            raise ValidationError("A journal line cannot have both debit and credit.")

    @property
    def signed_balance(self):
        if self.account.account_type in {Account.AccountType.ASSET, Account.AccountType.EXPENSE}:
            return self.debit - self.credit
        return self.credit - self.debit

    def __str__(self):
        return f"{self.journal_entry} - {self.account}"


class Budget(TimeStampedModel):
    year = models.PositiveIntegerField()
    department = models.CharField(max_length=30, choices=DepartmentChoices.choices)
    category = models.CharField(max_length=100)
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-year", "department", "category"]
        unique_together = ("year", "department", "category")

    def save(self, *args, **kwargs):
        self.remaining_amount = self.allocated_amount - self.spent_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.year} {self.department} - {self.category}"


class Expense(TimeStampedModel):
    expense_date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_expenses"
    )
    receipt_no = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-expense_date"]

    def __str__(self):
        return f"{self.category} - {self.amount}"
