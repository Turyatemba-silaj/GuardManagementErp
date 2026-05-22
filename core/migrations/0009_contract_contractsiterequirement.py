import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def migrate_existing_contract_data(apps, schema_editor):
    Client = apps.get_model("core", "Client")
    Contract = apps.get_model("core", "Contract")
    ContractSiteRequirement = apps.get_model("core", "ContractSiteRequirement")
    Site = apps.get_model("core", "Site")

    for client in Client.objects.all():
        contract_number = f"CON-{client.id:05d}"
        contract, _created = Contract.objects.get_or_create(
            contract_number=contract_number,
            defaults={
                "client": client,
                "service_type": "Manned Guarding",
                "start_date": client.contract_start_date or timezone.localdate(),
                "end_date": client.contract_end_date,
                "status": client.contract_status,
            },
        )
        for site in Site.objects.filter(client=client):
            required_guards = site.required_guards_per_shift or 1
            ContractSiteRequirement.objects.get_or_create(
                contract=contract,
                site=site,
                shift=None,
                start_date=contract.start_date,
                defaults={
                    "required_guards": required_guards,
                    "end_date": contract.end_date,
                    "status": contract.status,
                    "notes": "Migrated from site required guards per shift.",
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_site_required_guards_per_shift"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("contract_number", models.CharField(max_length=80, unique=True)),
                ("service_type", models.CharField(default="Manned Guarding", max_length=120)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("billing_rate", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid"), ("unpaid", "Unpaid"), ("closed", "Closed")], default="active", max_length=20)),
                ("terms", models.TextField(blank=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contracts", to="core.client")),
            ],
            options={
                "ordering": ["client__client_name", "-start_date", "contract_number"],
            },
        ),
        migrations.CreateModel(
            name="ContractSiteRequirement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("required_guards", models.PositiveIntegerField(default=1)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid"), ("unpaid", "Unpaid"), ("closed", "Closed")], default="active", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_requirements", to="core.contract")),
                ("shift", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="contract_requirements", to="core.shift")),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contract_requirements", to="core.site")),
            ],
            options={
                "ordering": ["site__site_name", "shift__start_time", "start_date"],
                "constraints": [models.UniqueConstraint(fields=("contract", "site", "shift", "start_date"), name="unique_contract_site_shift_start")],
            },
        ),
        migrations.RunPython(migrate_existing_contract_data, migrations.RunPython.noop),
    ]
