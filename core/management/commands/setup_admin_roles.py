from django.core.management.base import BaseCommand

from core.permissions import sync_system_admin_role


class Command(BaseCommand):
    help = "Create ERP admin roles and optionally assign all active staff users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--assign-active-staff",
            action="store_true",
            help="Add every active staff user to the System Administrator role.",
        )

    def handle(self, *args, **options):
        group, assigned_users = sync_system_admin_role(assign_active_staff=options["assign_active_staff"])
        self.stdout.write(self.style.SUCCESS(f"Synced role: {group.name}"))
        self.stdout.write(f"Permissions: {group.permissions.count()}")
        if assigned_users:
            self.stdout.write(f"Assigned users: {', '.join(assigned_users)}")
