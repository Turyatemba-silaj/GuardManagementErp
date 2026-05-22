from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_employee_next_of_keen_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="employee",
            name="armed_status",
        ),
        migrations.RemoveField(
            model_name="employee",
            name="license_no",
        ),
    ]
