import django.db.models.deletion
from django.db import migrations, models


def copy_profiles_to_employees(apps, schema_editor):
    Employee = apps.get_model("core", "Employee")
    Guard = apps.get_model("core", "Guard")
    Supervisor = apps.get_model("core", "Supervisor")
    Deployment = apps.get_model("core", "Deployment")
    GuardSchedule = apps.get_model("core", "GuardSchedule")
    Incident = apps.get_model("core", "Incident")
    PatrolLog = apps.get_model("core", "PatrolLog")
    Zone = apps.get_model("core", "Zone")
    ZoneGuardAllocation = apps.get_model("core", "ZoneGuardAllocation")

    for guard in Guard.objects.select_related("employee"):
        employee = guard.employee
        employee.badge_number = guard.badge_number
        employee.uniform_size = guard.uniform_size
        employee.qualification = guard.qualification
        employee.armed_status = guard.armed_status
        employee.training_level = guard.training_level
        employee.license_no = guard.license_no
        employee.save(
            update_fields=[
                "badge_number",
                "uniform_size",
                "qualification",
                "armed_status",
                "training_level",
                "license_no",
                "updated_at",
            ]
        )

    for supervisor in Supervisor.objects.select_related("employee"):
        employee = supervisor.employee
        employee.assigned_zone = supervisor.assigned_zone
        employee.experience_years = supervisor.experience_years
        employee.authority_level = supervisor.authority_level
        employee.save(update_fields=["assigned_zone", "experience_years", "authority_level", "updated_at"])

    for deployment in Deployment.objects.select_related("guard__employee", "supervisor__employee"):
        deployment.employee_new_id = deployment.guard.employee_id
        deployment.supervisor_new_id = deployment.supervisor.employee_id if deployment.supervisor_id else None
        deployment.save(update_fields=["employee_new", "supervisor_new", "updated_at"])

    for schedule in GuardSchedule.objects.select_related("guard__employee", "replacement_guard__employee"):
        schedule.employee_new_id = schedule.guard.employee_id
        schedule.replacement_employee_new_id = (
            schedule.replacement_guard.employee_id if schedule.replacement_guard_id else None
        )
        schedule.save(update_fields=["employee_new", "replacement_employee_new", "updated_at"])

    for incident in Incident.objects.select_related("guard__employee"):
        incident.employee_new_id = incident.guard.employee_id
        incident.save(update_fields=["employee_new", "updated_at"])

    for patrol_log in PatrolLog.objects.select_related("guard__employee"):
        patrol_log.employee_new_id = patrol_log.guard.employee_id
        patrol_log.save(update_fields=["employee_new", "updated_at"])

    for zone in Zone.objects.select_related("supervisor__employee"):
        zone.supervisor_new_id = zone.supervisor.employee_id
        zone.save(update_fields=["supervisor_new", "updated_at"])

    for allocation in ZoneGuardAllocation.objects.select_related("guard__employee"):
        allocation.employee_new_id = allocation.guard.employee_id
        allocation.save(update_fields=["employee_new", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_set_uganda_shift_hours"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="armed_status",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="employee",
            name="assigned_zone",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="employee",
            name="authority_level",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="employee",
            name="badge_number",
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="employee",
            name="experience_years",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="employee",
            name="license_no",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="employee",
            name="qualification",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="employee",
            name="training_level",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="employee",
            name="uniform_size",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="deployment",
            name="employee_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deployments",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="deployment",
            name="supervisor_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supervised_deployments",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="guardschedule",
            name="employee_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schedules",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="guardschedule",
            name="replacement_employee_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replacement_schedules",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="incident",
            name="employee_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incidents",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="patrollog",
            name="employee_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="patrol_logs",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="zone",
            name="supervisor_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="supervised_zones",
                to="core.employee",
            ),
        ),
        migrations.AddField(
            model_name="zoneguardallocation",
            name="employee_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="zone_allocations",
                to="core.employee",
            ),
        ),
        migrations.RunPython(copy_profiles_to_employees, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="zoneguardallocation",
            name="unique_active_guard_zone",
        ),
        migrations.RemoveField(model_name="deployment", name="guard"),
        migrations.RemoveField(model_name="deployment", name="supervisor"),
        migrations.RemoveField(model_name="guardschedule", name="guard"),
        migrations.RemoveField(model_name="guardschedule", name="replacement_guard"),
        migrations.RemoveField(model_name="incident", name="guard"),
        migrations.RemoveField(model_name="patrollog", name="guard"),
        migrations.RemoveField(model_name="zone", name="supervisor"),
        migrations.RemoveField(model_name="zoneguardallocation", name="guard"),
        migrations.RenameField(model_name="deployment", old_name="employee_new", new_name="employee"),
        migrations.RenameField(model_name="deployment", old_name="supervisor_new", new_name="supervisor"),
        migrations.RenameField(model_name="guardschedule", old_name="employee_new", new_name="employee"),
        migrations.RenameField(
            model_name="guardschedule",
            old_name="replacement_employee_new",
            new_name="replacement_employee",
        ),
        migrations.RenameField(model_name="incident", old_name="employee_new", new_name="employee"),
        migrations.RenameField(model_name="patrollog", old_name="employee_new", new_name="employee"),
        migrations.RenameField(model_name="zone", old_name="supervisor_new", new_name="supervisor"),
        migrations.RenameField(model_name="zoneguardallocation", old_name="employee_new", new_name="employee"),
        migrations.RenameModel(old_name="ZoneGuardAllocation", new_name="ZoneEmployeeAllocation"),
        migrations.AlterModelOptions(
            name="guardschedule",
            options={"ordering": ["shift_date", "shift__start_time", "employee__first_name"]},
        ),
        migrations.AlterModelOptions(
            name="zoneemployeeallocation",
            options={"ordering": ["zone", "employee__first_name"]},
        ),
        migrations.AlterField(
            model_name="zoneemployeeallocation",
            name="zone",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="employee_allocations",
                to="core.zone",
            ),
        ),
        migrations.AlterField(
            model_name="deployment",
            name="employee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deployments",
                to="core.employee",
            ),
        ),
        migrations.AlterField(
            model_name="guardschedule",
            name="employee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="schedules",
                to="core.employee",
            ),
        ),
        migrations.AlterField(
            model_name="incident",
            name="employee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="incidents",
                to="core.employee",
            ),
        ),
        migrations.AlterField(
            model_name="patrollog",
            name="employee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="patrol_logs",
                to="core.employee",
            ),
        ),
        migrations.AlterField(
            model_name="zone",
            name="supervisor",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="supervised_zones",
                to="core.employee",
            ),
        ),
        migrations.AlterField(
            model_name="zoneemployeeallocation",
            name="employee",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="zone_allocations",
                to="core.employee",
            ),
        ),
        migrations.AddConstraint(
            model_name="zoneemployeeallocation",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="active", end_date__isnull=True),
                fields=("employee",),
                name="unique_active_employee_zone",
            ),
        ),
        migrations.DeleteModel(name="Guard"),
        migrations.DeleteModel(name="Supervisor"),
    ]
