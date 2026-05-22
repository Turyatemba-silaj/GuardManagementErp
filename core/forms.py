from django import forms

from . import models


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = models.Invoice
        fields = (
            "client",
            "contract",
            "billing_scope",
            "site",
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
            "billing_scope": "Choose one site or invoice every active site on the selected contract.",
            "site": "Required when invoicing one site. Leave blank when invoicing all contract sites.",
            "guard_count": "Automatically calculated from the selected contract site requirements when available.",
            "rate_per_guard": "Automatically pulled from the contract site requirement or parent contract.",
        }
        widgets = {
            "billing_month": forms.DateInput(attrs={"type": "date"}),
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["client"].required = False
        self.fields["client"].widget.attrs["readonly"] = "readonly"
        self.fields["client"].help_text = "Automatically selected from the contract."
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
            self.fields["site"].queryset = models.Site.objects.filter(
                contract_requirements__contract=contract
            ).distinct().order_by("site_name")
        else:
            self.fields["site"].queryset = models.Site.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        contract = cleaned_data.get("contract")
        billing_scope = cleaned_data.get("billing_scope")
        site = cleaned_data.get("site")
        if contract:
            cleaned_data["client"] = contract.client
        if billing_scope == models.Invoice.BillingScope.SITE and not site:
            self.add_error("site", "Select a site, or choose all contract sites.")
        if contract and site and site.client_id != contract.client_id:
            self.add_error("site", "Selected site must belong to the contract client.")
        if contract and site and not models.ContractSiteRequirement.objects.filter(contract=contract, site=site).exists():
            self.add_error("site", "Selected site is not part of this contract.")
        return cleaned_data
