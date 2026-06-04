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
        "contract_value",
        "currency",
        "billing_cycle",
        "payment_terms_days",
        "termination_notice_days",
        "governing_law",
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
            "contract_number",
            "contract_title",
            "service_type",
            "client_representative",
            "client_representative_title",
            "client_representative_email",
            "company_representative",
            "company_representative_title",
            "signed_date",
            "start_date",
            "end_date",
            "billing_rate",
            "contract_value",
            "currency",
            "billing_cycle",
            "payment_terms_days",
            "payment_instructions",
            "status",
            "service_scope",
            "service_location",
            "service_hours",
            "response_time_sla",
            "supervision_frequency",
            "guard_training_requirements",
            "client_obligations",
            "company_obligations",
            "confidentiality_clause",
            "liability_limit",
            "termination_notice_days",
            "renewal_terms",
            "governing_law",
            "special_conditions",
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
            "contract_title": "Contract Title",
            "client_representative": "Client Representative",
            "client_representative_title": "Client Representative Title",
            "client_representative_email": "Client Representative Email",
            "company_representative": "Company Representative",
            "company_representative_title": "Company Representative Title",
            "signed_date": "Signed Date",
            "billing_rate": "Billing Rate",
            "contract_value": "Contract Value",
            "billing_cycle": "Billing Cycle",
            "payment_terms_days": "Payment Terms Days",
            "payment_instructions": "Payment Instructions",
            "service_scope": "Scope of Services",
            "service_location": "Service Location",
            "service_hours": "Service Hours",
            "response_time_sla": "Response Time SLA",
            "supervision_frequency": "Supervision Frequency",
            "guard_training_requirements": "Guard Training Requirements",
            "client_obligations": "Client Obligations",
            "company_obligations": "Company Obligations",
            "confidentiality_clause": "Confidentiality Clause",
            "liability_limit": "Liability Limit",
            "termination_notice_days": "Termination Notice Days",
            "renewal_terms": "Renewal Terms",
            "governing_law": "Governing Law",
            "special_conditions": "Special Conditions",
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
            "contract_value": "Total contract value when agreed. Leave 0 if billed only by deployment requirements.",
            "payment_terms_days": "Number of days after invoice date before payment is due.",
            "termination_notice_days": "Required notice period before either party can terminate.",
        }
        widgets = {
            "signed_date": forms.DateInput(attrs={"type": "date"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "payment_instructions": forms.Textarea(attrs={"rows": 3}),
            "service_scope": forms.Textarea(attrs={"rows": 4}),
            "guard_training_requirements": forms.Textarea(attrs={"rows": 3}),
            "client_obligations": forms.Textarea(attrs={"rows": 3}),
            "company_obligations": forms.Textarea(attrs={"rows": 3}),
            "confidentiality_clause": forms.Textarea(attrs={"rows": 3}),
            "renewal_terms": forms.Textarea(attrs={"rows": 3}),
            "special_conditions": forms.Textarea(attrs={"rows": 3}),
            "terms": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["currency"].initial = self.fields["currency"].initial or "UGX"
        self.fields["billing_cycle"].initial = self.fields["billing_cycle"].initial or models.Contract.BillingCycle.MONTHLY
        self.fields["payment_terms_days"].initial = self.fields["payment_terms_days"].initial or 30
        self.fields["termination_notice_days"].initial = self.fields["termination_notice_days"].initial or 30
        self.fields["governing_law"].initial = self.fields["governing_law"].initial or "Uganda"
        for field_name in self.DEFAULTED_FIELDS:
            self.fields[field_name].required = False
        for field_name in self.DELIVERABLE_FIELDS:
            self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["contract_value"] = cleaned_data.get("contract_value") or 0
        cleaned_data["currency"] = (cleaned_data.get("currency") or "UGX").upper()
        cleaned_data["billing_cycle"] = cleaned_data.get("billing_cycle") or models.Contract.BillingCycle.MONTHLY
        cleaned_data["payment_terms_days"] = cleaned_data.get("payment_terms_days") or 30
        cleaned_data["termination_notice_days"] = cleaned_data.get("termination_notice_days") or 30
        cleaned_data["governing_law"] = cleaned_data.get("governing_law") or "Uganda"
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
