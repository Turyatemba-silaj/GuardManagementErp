from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from . import models
from .security import validate_model_upload


User = get_user_model()


class SecureModelForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        for field_name, uploaded_file in self.files.items():
            validate_model_upload(field_name, uploaded_file)
        return cleaned_data


class RolePermissionForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select exactly what users in this role can view, add, change, or delete.",
    )

    class Meta:
        model = Group
        fields = ("name", "permissions")
        labels = {"name": "Role Name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class UserRoleForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to keep the current password.",
    )
    groups = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Group.objects.order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    user_permissions = forms.ModelMultipleChoiceField(
        label="Direct Permissions",
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Use direct permissions for exceptions. Prefer roles for normal access.",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "groups",
            "user_permissions",
            "is_active",
            "is_staff",
        )
        labels = {"is_staff": "Can access staff areas"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        for checkbox_name in ("groups", "user_permissions", "is_active", "is_staff"):
            self.fields[checkbox_name].widget.attrs.pop("class", None)

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.instance.pk and not password:
            raise forms.ValidationError("Enter an initial password for this user.")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        password = self.cleaned_data.pop("password", "")
        user = super().save(commit=False)
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self.save_m2m()
        return user


class ContractForm(SecureModelForm):
    DEFAULTED_FIELDS = (
        "contract_type",
        "contract_value",
        "monthly_contract_value",
        "annual_contract_value",
        "currency",
        "billing_cycle",
        "payment_terms",
        "payment_terms_days",
        "vat_rate",
        "termination_notice_days",
        "renewal_reminder_days",
        "governing_law",
        "uniform_requirement",
        "arming_status",
        "day_guards_required",
        "night_guards_required",
        "supervisors_required",
    )
    DELIVERABLE_FIELDS = (
        "dog_count",
        "dog_rate",
        "metal_detector_count",
        "metal_detector_rate",
        "walk_through_detector_count",
        "walk_through_detector_rate",
        "panic_baton_count",
        "panic_baton_rate",
        "handcuffs_count",
        "handcuffs_rate",
    )

    class Meta:
        model = models.Contract
        fields = (
            "client",
            "deployment_site",
            "contract_number",
            "contract_title",
            "contract_type",
            "service_type",
            "contract_manager",
            "client_representative",
            "client_representative_title",
            "client_representative_phone",
            "client_representative_email",
            "company_representative",
            "company_representative_title",
            "signed_date",
            "start_date",
            "end_date",
            "renewal_date",
            "renewal_reminder_days",
            "billing_rate",
            "monthly_contract_value",
            "annual_contract_value",
            "contract_value",
            "currency",
            "billing_cycle",
            "payment_terms",
            "payment_terms_days",
            "payment_instructions",
            "vat_applicable",
            "vat_rate",
            "status",
            "service_scope",
            "service_location",
            "service_hours",
            "response_time_sla",
            "incident_escalation_time",
            "patrol_frequency",
            "supervision_frequency",
            "guard_training_requirements",
            "day_guards_required",
            "night_guards_required",
            "supervisors_required",
            "shift_pattern",
            "arming_status",
            "patrol_required",
            "radio_required",
            "torch_required",
            "metal_detector_required",
            "vehicle_required",
            "uniform_requirement",
            "client_obligations",
            "company_obligations",
            "confidentiality_clause",
            "liability_limit",
            "termination_notice_days",
            "renewal_terms",
            "governing_law",
            "special_conditions",
            "late_payment_penalty",
            "service_breach_penalty",
            "signed_contract",
            "amendment_document",
            "renewal_document",
            "dog_count",
            "dog_rate",
            "metal_detector_count",
            "metal_detector_rate",
            "walk_through_detector_count",
            "walk_through_detector_rate",
            "panic_baton_count",
            "panic_baton_rate",
            "handcuffs_count",
            "handcuffs_rate",
            "terms",
        )
        labels = {
            "deployment_site": "Deployment Site",
            "contract_title": "Contract Title",
            "contract_type": "Contract Type",
            "contract_manager": "Contract Manager",
            "client_representative": "Client Representative",
            "client_representative_title": "Client Representative Title",
            "client_representative_phone": "Client Phone Number",
            "client_representative_email": "Client Representative Email",
            "company_representative": "Company Representative",
            "company_representative_title": "Company Representative Title",
            "signed_date": "Signed Date",
            "renewal_date": "Renewal Date",
            "renewal_reminder_days": "Renewal Reminder Days",
            "billing_rate": "Billing Rate",
            "monthly_contract_value": "Monthly Contract Value",
            "annual_contract_value": "Annual Contract Value",
            "contract_value": "Total Contract Value",
            "billing_cycle": "Billing Frequency",
            "payment_terms": "Payment Terms",
            "payment_terms_days": "Payment Terms Days",
            "payment_instructions": "Payment Instructions",
            "vat_applicable": "VAT Applicable",
            "vat_rate": "VAT Rate",
            "service_scope": "Scope of Services",
            "service_location": "Service Location",
            "service_hours": "Service Hours",
            "response_time_sla": "Response Time SLA",
            "incident_escalation_time": "Incident Escalation Time",
            "patrol_frequency": "Patrol Frequency",
            "supervision_frequency": "Supervision Frequency",
            "guard_training_requirements": "Guard Training Requirements",
            "day_guards_required": "Day Guards",
            "night_guards_required": "Night Guards",
            "supervisors_required": "Supervisors",
            "shift_pattern": "Shift Pattern",
            "arming_status": "Armed / Unarmed",
            "patrol_required": "Patrol Required",
            "radio_required": "Radio Required",
            "torch_required": "Torch Required",
            "metal_detector_required": "Metal Detector Required",
            "vehicle_required": "Vehicle Required",
            "uniform_requirement": "Uniform Requirement",
            "client_obligations": "Client Obligations",
            "company_obligations": "Company Obligations",
            "confidentiality_clause": "Confidentiality Clause",
            "liability_limit": "Liability Limit",
            "termination_notice_days": "Termination Notice Days",
            "renewal_terms": "Renewal Terms",
            "governing_law": "Governing Law",
            "special_conditions": "Special Conditions",
            "late_payment_penalty": "Late Payment Penalty",
            "service_breach_penalty": "Service Breach Penalty",
            "signed_contract": "Signed Contract PDF",
            "amendment_document": "Amendment Document",
            "renewal_document": "Renewal Document",
            "dog_count": "Dogs",
            "dog_rate": "Price Per Dog",
            "metal_detector_count": "Metal Detectors",
            "metal_detector_rate": "Price Per Metal Detector",
            "walk_through_detector_count": "Walk Through Detectors",
            "walk_through_detector_rate": "Price Per Walk Through Detector",
            "panic_baton_count": "Panic Batons",
            "panic_baton_rate": "Price Per Panic Baton",
            "handcuffs_count": "Handcuffs",
            "handcuffs_rate": "Price Per Handcuff",
        }
        help_texts = {
            "service_type": "Select Others to record additional contract deliverables.",
            "monthly_contract_value": "Example: UGX 5,900,000.",
            "annual_contract_value": "Example: UGX 70,800,000.",
            "contract_value": "Overall value for one-time or framework contracts. Monthly/annual values can be calculated from it when blank.",
            "payment_terms_days": "Number of days after invoice date before payment is due.",
            "termination_notice_days": "Required notice period before either party can terminate.",
            "vat_rate": "Use 0.18 for 18% VAT.",
            "renewal_reminder_days": "Days before renewal or expiry when management should be alerted.",
        }
        widgets = {
            "signed_date": forms.DateInput(attrs={"type": "date"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "renewal_date": forms.DateInput(attrs={"type": "date"}),
            "payment_instructions": forms.Textarea(attrs={"rows": 3}),
            "service_scope": forms.Textarea(attrs={"rows": 4}),
            "guard_training_requirements": forms.Textarea(attrs={"rows": 3}),
            "client_obligations": forms.Textarea(attrs={"rows": 3}),
            "company_obligations": forms.Textarea(attrs={"rows": 3}),
            "confidentiality_clause": forms.Textarea(attrs={"rows": 3}),
            "renewal_terms": forms.Textarea(attrs={"rows": 3}),
            "special_conditions": forms.Textarea(attrs={"rows": 3}),
            "signed_contract": forms.FileInput(attrs={"accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png"}),
            "amendment_document": forms.FileInput(attrs={"accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png"}),
            "renewal_document": forms.FileInput(attrs={"accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png"}),
            "terms": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        client = None
        client_id = self.data.get("client") if self.data else None
        if client_id:
            try:
                client = models.Client.objects.get(pk=client_id)
            except (TypeError, ValueError, models.Client.DoesNotExist):
                client = None
        elif self.instance and self.instance.pk:
            client = self.instance.client
        if client:
            self.fields["deployment_site"].queryset = models.Site.objects.filter(client=client).order_by("site_name")
        else:
            self.fields["deployment_site"].queryset = models.Site.objects.none()

        self.fields["contract_manager"].queryset = models.Employee.objects.order_by("first_name", "last_name")
        self.fields["contract_type"].initial = self.fields["contract_type"].initial or models.Contract.ContractType.FIXED_TERM
        self.fields["currency"].initial = self.fields["currency"].initial or models.Contract.Currency.UGX
        self.fields["billing_cycle"].initial = self.fields["billing_cycle"].initial or models.Contract.BillingCycle.MONTHLY
        self.fields["payment_terms"].initial = self.fields["payment_terms"].initial or models.Contract.PaymentTerm.NET_30
        self.fields["payment_terms_days"].initial = self.fields["payment_terms_days"].initial or 30
        self.fields["vat_rate"].initial = self.fields["vat_rate"].initial or "0.18"
        self.fields["termination_notice_days"].initial = self.fields["termination_notice_days"].initial or 30
        self.fields["renewal_reminder_days"].initial = self.fields["renewal_reminder_days"].initial or 60
        self.fields["governing_law"].initial = self.fields["governing_law"].initial or "Uganda"
        self.fields["uniform_requirement"].initial = self.fields["uniform_requirement"].initial or models.Contract.UniformRequirement.COMPANY
        self.fields["arming_status"].initial = self.fields["arming_status"].initial or models.Contract.ArmingStatus.UNARMED
        for field_name in self.DEFAULTED_FIELDS:
            self.fields[field_name].required = False
        for field_name in self.DELIVERABLE_FIELDS:
            self.fields[field_name].required = False
        for field_name in ("vat_applicable", "patrol_required", "radio_required", "torch_required", "metal_detector_required", "vehicle_required"):
            self.fields[field_name].widget.attrs.pop("class", None)

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get("client")
        deployment_site = cleaned_data.get("deployment_site")
        if client and deployment_site and deployment_site.client_id != client.id:
            self.add_error("deployment_site", "Deployment site must belong to the selected client.")

        monthly_value = cleaned_data.get("monthly_contract_value") or 0
        annual_value = cleaned_data.get("annual_contract_value") or 0
        contract_value = cleaned_data.get("contract_value") or 0
        if not annual_value and monthly_value:
            annual_value = monthly_value * 12
        if not monthly_value and annual_value:
            monthly_value = annual_value / 12
        if not contract_value:
            contract_value = annual_value or monthly_value
        cleaned_data["monthly_contract_value"] = monthly_value
        cleaned_data["annual_contract_value"] = annual_value
        cleaned_data["contract_value"] = cleaned_data.get("contract_value") or 0
        cleaned_data["contract_value"] = contract_value
        cleaned_data["currency"] = (cleaned_data.get("currency") or models.Contract.Currency.UGX).upper()
        cleaned_data["billing_cycle"] = cleaned_data.get("billing_cycle") or models.Contract.BillingCycle.MONTHLY
        cleaned_data["contract_type"] = cleaned_data.get("contract_type") or models.Contract.ContractType.FIXED_TERM
        cleaned_data["payment_terms"] = cleaned_data.get("payment_terms") or models.Contract.PaymentTerm.NET_30
        if cleaned_data["payment_terms"] == models.Contract.PaymentTerm.NET_30:
            cleaned_data["payment_terms_days"] = 30
        elif cleaned_data["payment_terms"] == models.Contract.PaymentTerm.NET_60:
            cleaned_data["payment_terms_days"] = 60
        elif cleaned_data["payment_terms"] == models.Contract.PaymentTerm.ADVANCE:
            cleaned_data["payment_terms_days"] = 0
        else:
            cleaned_data["payment_terms_days"] = cleaned_data.get("payment_terms_days") or 30
        cleaned_data["payment_terms_days"] = cleaned_data.get("payment_terms_days") or 30
        if cleaned_data["payment_terms"] == models.Contract.PaymentTerm.ADVANCE:
            cleaned_data["payment_terms_days"] = 0
        cleaned_data["vat_rate"] = cleaned_data.get("vat_rate") or Decimal("0.18")
        cleaned_data["termination_notice_days"] = cleaned_data.get("termination_notice_days") or 30
        cleaned_data["renewal_reminder_days"] = cleaned_data.get("renewal_reminder_days") or 60
        cleaned_data["governing_law"] = cleaned_data.get("governing_law") or "Uganda"
        cleaned_data["uniform_requirement"] = cleaned_data.get("uniform_requirement") or models.Contract.UniformRequirement.COMPANY
        cleaned_data["arming_status"] = cleaned_data.get("arming_status") or models.Contract.ArmingStatus.UNARMED
        cleaned_data["day_guards_required"] = cleaned_data.get("day_guards_required") or 0
        cleaned_data["night_guards_required"] = cleaned_data.get("night_guards_required") or 0
        cleaned_data["supervisors_required"] = cleaned_data.get("supervisors_required") or 0
        if cleaned_data.get("service_type") != models.Contract.ServiceType.OTHERS:
            for field_name in self.DELIVERABLE_FIELDS:
                cleaned_data[field_name] = 0
        else:
            for field_name in self.DELIVERABLE_FIELDS:
                cleaned_data[field_name] = cleaned_data.get(field_name) or 0
        return cleaned_data


class ContractSiteRequirementForm(SecureModelForm):
    client = forms.ModelChoiceField(
        queryset=models.Client.objects.order_by("client_name"),
        help_text="Select the client first. Contracts and site code are prepared from this client.",
    )
    generated_site_code = forms.CharField(
        label="Generated Site Code",
        required=False,
        disabled=True,
        help_text="Generated automatically when a new site is saved.",
    )
    site_name = forms.CharField(required=False, help_text="Required when creating a new site.")
    site_address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    city = forms.CharField(required=False)

    class Meta:
        model = models.ContractSiteRequirement
        fields = (
            "client",
            "contract",
            "generated_site_code",
            "site_name",
            "site_address",
            "city",
            "shift",
            "required_guards",
            "rate_per_guard",
            "gun_count",
            "gun_rate",
            "radio_count",
            "radio_rate",
            "metal_detector_count",
            "metal_detector_rate",
            "walk_through_machine_count",
            "walk_through_machine_rate",
            "dog_count",
            "dog_rate",
            "panic_baton_count",
            "panic_baton_rate",
            "handcuffs_count",
            "handcuffs_rate",
            "start_date",
            "end_date",
            "status",
            "notes",
        )
        labels = {
            "rate_per_guard": "Rate Per Guard",
            "walk_through_machine_count": "Walk Through Detectors",
            "walk_through_machine_rate": "Price Per Walk Through Detector",
            "panic_baton_count": "Panic Batons",
            "panic_baton_rate": "Price Per Panic Baton",
            "handcuffs_count": "Handcuffs",
            "handcuffs_rate": "Price Per Handcuff",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        client = None
        contract = None
        client_id = self.data.get("client") if self.data else None
        contract_id = self.data.get("contract") if self.data else None

        if client_id:
            try:
                client = models.Client.objects.get(pk=client_id)
            except (TypeError, ValueError, models.Client.DoesNotExist):
                client = None
        elif instance and instance.pk:
            client = instance.contract.client
            self.fields["client"].initial = client
            self.fields["site_name"].initial = instance.site.site_name
            self.fields["site_address"].initial = instance.site.site_address
            self.fields["city"].initial = instance.site.city

        if contract_id:
            try:
                contract = models.Contract.objects.get(pk=contract_id)
            except (TypeError, ValueError, models.Contract.DoesNotExist):
                contract = None
        elif instance and instance.pk:
            contract = instance.contract

        if client:
            self.fields["contract"].queryset = models.Contract.objects.filter(client=client).order_by("-start_date", "contract_number")
            self.fields["generated_site_code"].initial = self.next_site_code(client)
        else:
            self.fields["contract"].queryset = models.Contract.objects.none()

        if contract and not self.data:
            self.apply_contract_initials(contract)

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        for field_name in (
            "rate_per_guard",
            "gun_count",
            "gun_rate",
            "radio_count",
            "radio_rate",
            "metal_detector_count",
            "metal_detector_rate",
            "walk_through_machine_count",
            "walk_through_machine_rate",
            "dog_count",
            "dog_rate",
            "panic_baton_count",
            "panic_baton_rate",
            "handcuffs_count",
            "handcuffs_rate",
            "start_date",
            "end_date",
        ):
            self.fields[field_name].required = False
            self.fields[field_name].widget.attrs["data-contract-fill"] = "true"

    @staticmethod
    def next_site_code(client):
        return models.Site.next_site_code()

    def apply_contract_initials(self, contract):
        self.fields["rate_per_guard"].initial = contract.billing_rate
        self.fields["start_date"].initial = contract.start_date
        self.fields["end_date"].initial = contract.end_date
        self.fields["dog_count"].initial = contract.dog_count
        self.fields["dog_rate"].initial = contract.dog_rate
        self.fields["metal_detector_count"].initial = contract.metal_detector_count
        self.fields["metal_detector_rate"].initial = contract.metal_detector_rate
        self.fields["walk_through_machine_count"].initial = contract.walk_through_detector_count
        self.fields["walk_through_machine_rate"].initial = contract.walk_through_detector_rate
        self.fields["panic_baton_count"].initial = contract.panic_baton_count
        self.fields["panic_baton_rate"].initial = contract.panic_baton_rate
        self.fields["handcuffs_count"].initial = contract.handcuffs_count
        self.fields["handcuffs_rate"].initial = contract.handcuffs_rate

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get("client")
        contract = cleaned_data.get("contract")
        site_name = (cleaned_data.get("site_name") or "").strip()
        site_address = (cleaned_data.get("site_address") or "").strip()
        city = (cleaned_data.get("city") or "").strip()

        if contract and client and contract.client_id != client.id:
            self.add_error("contract", "Selected contract must belong to the selected client.")
        if not site_name:
            self.add_error("site_name", "Enter the site name.")
        if not site_address:
            self.add_error("site_address", "Enter the site address.")
        if not city:
            self.add_error("city", "Enter the city.")

        if contract:
            cleaned_data["rate_per_guard"] = contract.billing_rate
            cleaned_data["start_date"] = contract.start_date
            cleaned_data["end_date"] = contract.end_date
            cleaned_data["dog_count"] = contract.dog_count
            cleaned_data["dog_rate"] = contract.dog_rate
            cleaned_data["metal_detector_count"] = contract.metal_detector_count
            cleaned_data["metal_detector_rate"] = contract.metal_detector_rate
            cleaned_data["walk_through_machine_count"] = contract.walk_through_detector_count
            cleaned_data["walk_through_machine_rate"] = contract.walk_through_detector_rate
            cleaned_data["panic_baton_count"] = contract.panic_baton_count
            cleaned_data["panic_baton_rate"] = contract.panic_baton_rate
            cleaned_data["handcuffs_count"] = contract.handcuffs_count
            cleaned_data["handcuffs_rate"] = contract.handcuffs_rate
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        site = instance.site if instance.pk and instance.site_id else None
        if site:
            site.client = self.cleaned_data["client"]
            site.site_name = self.cleaned_data["site_name"]
            site.site_address = self.cleaned_data["site_address"]
            site.city = self.cleaned_data["city"]
            site.save()
        else:
            site = models.Site(
                client=self.cleaned_data["client"],
                site_name=self.cleaned_data["site_name"],
                site_address=self.cleaned_data["site_address"],
                city=self.cleaned_data["city"],
            )
            site.save()
        instance.site = site
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class InvoiceForm(forms.ModelForm):
    OPTIONAL_AMOUNT_FIELDS = (
        "gun_count",
        "gun_rate",
        "radio_count",
        "radio_rate",
        "metal_detector_count",
        "metal_detector_rate",
        "walk_through_machine_count",
        "walk_through_machine_rate",
        "dog_count",
        "dog_rate",
    )

    class Meta:
        model = models.Invoice
        fields = (
            "client",
            "contract",
            "billing_scope",
            "site",
            "selected_sites",
            "billing_month",
            "invoice_date",
            "due_date",
            "guard_count",
            "rate_per_guard",
            "gun_count",
            "gun_rate",
            "radio_count",
            "radio_rate",
            "metal_detector_count",
            "metal_detector_rate",
            "walk_through_machine_count",
            "walk_through_machine_rate",
            "dog_count",
            "dog_rate",
            "paid_amount",
        )
        labels = {
            "billing_scope": "Invoice Scope",
            "billing_month": "Billing Month",
            "guard_count": "Number of Guards",
            "rate_per_guard": "Rate Per Guard",
            "gun_count": "Guns",
            "gun_rate": "Rate Per Gun",
            "radio_count": "Radios",
            "radio_rate": "Rate Per Radio",
            "metal_detector_count": "Metal Detectors",
            "metal_detector_rate": "Rate Per Metal Detector",
            "walk_through_machine_count": "Walk Through Machines",
            "walk_through_machine_rate": "Rate Per Walk Through Machine",
            "dog_count": "Dogs",
            "dog_rate": "Rate Per Dog",
        }
        help_texts = {
            "billing_month": "Use the first day of the billing month, for example 2026-05-01.",
            "billing_scope": "Choose one site, selected sites, or every active site on the selected contract.",
            "site": "Required when invoicing one site.",
            "selected_sites": "Choose two or more sites from the selected contract.",
            "guard_count": "Automatically calculated from the selected contract site requirements when available.",
            "rate_per_guard": "Automatically pulled from the contract site requirement or parent contract.",
        }
        widgets = {
            "selected_sites": forms.SelectMultiple(attrs={"size": 6}),
            "billing_month": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "invoice_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "due_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["billing_month"].required = True
        for field_name in self.OPTIONAL_AMOUNT_FIELDS:
            self.fields[field_name].required = False
        self.fields["client"].required = False
        self.fields["client"].widget.attrs["readonly"] = "readonly"
        self.fields["client"].help_text = "Automatically selected from the contract."
        self.fields["selected_sites"].required = False
        if not self.is_bound and not self.instance.pk:
            self.fields["billing_month"].initial = timezone.localdate().replace(day=1)
        contract = None
        contract_id = self.data.get("contract") if self.data else None
        if contract_id:
            try:
                contract = models.Contract.objects.get(pk=contract_id)
            except (TypeError, ValueError, models.Contract.DoesNotExist):
                contract = None
        elif self.instance and self.instance.contract_id:
            contract = self.instance.contract
        if contract:
            self.fields["client"].initial = contract.client
            contract_sites = models.Site.objects.filter(
                contract_requirements__contract=contract
            ).distinct().order_by("site_name")
            self.fields["site"].queryset = contract_sites
            self.fields["selected_sites"].queryset = contract_sites
        else:
            self.fields["site"].queryset = models.Site.objects.none()
            self.fields["selected_sites"].queryset = models.Site.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        contract = cleaned_data.get("contract")
        billing_scope = cleaned_data.get("billing_scope")
        site = cleaned_data.get("site")
        selected_sites = cleaned_data.get("selected_sites")
        if contract:
            cleaned_data["client"] = contract.client
        if billing_scope == models.Invoice.BillingScope.SITE and not site:
            self.add_error("site", "Select a site, selected sites, or all contract sites.")
        if billing_scope == models.Invoice.BillingScope.MULTIPLE_SITES and not selected_sites:
            self.add_error("selected_sites", "Select at least one contract site.")
        if contract and site and site.client_id != contract.client_id:
            self.add_error("site", "Selected site must belong to the contract client.")
        if contract and site and not models.ContractSiteRequirement.objects.filter(contract=contract, site=site).exists():
            self.add_error("site", "Selected site is not part of this contract.")
        if contract and selected_sites:
            invalid_sites = selected_sites.exclude(contract_requirements__contract=contract).distinct()
            if invalid_sites.exists():
                self.add_error("selected_sites", "Selected sites must belong to this contract.")
        if cleaned_data.get("billing_month"):
            cleaned_data["billing_month"] = cleaned_data["billing_month"].replace(day=1)
        for field_name in self.OPTIONAL_AMOUNT_FIELDS:
            cleaned_data[field_name] = cleaned_data.get(field_name) or 0
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected_sites = self.cleaned_data.get("selected_sites")
        if commit:
            instance.save()
            self.save_m2m()
            if instance.billing_scope == models.Invoice.BillingScope.MULTIPLE_SITES:
                instance.selected_sites.set(selected_sites)
                instance.save()
            else:
                instance.selected_sites.clear()
        return instance
