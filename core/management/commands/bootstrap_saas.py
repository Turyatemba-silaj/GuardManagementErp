from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import SubscriptionPlan, TenantMembership, TenantOrganization


class Command(BaseCommand):
    help = "Create a standard SaaS plan, tenant organization, and owner membership."

    def add_arguments(self, parser):
        parser.add_argument("--organization", default="Sentinel Security")
        parser.add_argument("--slug", default="sentinel-security")
        parser.add_argument("--owner-username", default=None)
        parser.add_argument("--domain", default="")

    def handle(self, *args, **options):
        owner_username = options["owner_username"] or settings.ERP_PERMANENT_LOGIN_USERNAME
        User = get_user_model()
        owner = User.objects.filter(username=owner_username).first()
        if not owner:
            self.stderr.write(self.style.ERROR(f"Owner user '{owner_username}' does not exist."))
            return

        plan, _ = SubscriptionPlan.objects.update_or_create(
            slug="standard",
            defaults={
                "name": "Standard",
                "monthly_price": "0.00",
                "user_limit": 25,
                "site_limit": 100,
                "is_active": True,
                "features": {
                    "operations": True,
                    "human_resources": True,
                    "finance": True,
                    "reports": True,
                },
            },
        )
        organization, _ = TenantOrganization.objects.update_or_create(
            slug=options["slug"],
            defaults={
                "name": options["organization"],
                "primary_domain": options["domain"] or None,
                "owner": owner,
                "plan": plan,
                "status": TenantOrganization.Status.ACTIVE,
                "trial_ends_at": None,
                "subscription_ends_at": None,
            },
        )
        TenantMembership.objects.update_or_create(
            organization=organization,
            user=owner,
            defaults={"role": TenantMembership.Role.OWNER, "is_active": True},
        )
        owner.is_active = True
        owner.is_staff = True
        owner.is_superuser = True
        owner.save(update_fields=["is_active", "is_staff", "is_superuser"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Bootstrapped {organization.name} on the {plan.name} plan for {owner.username} at {timezone.now():%Y-%m-%d %H:%M}."
            )
        )
