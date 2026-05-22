from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_merge_guard_supervisor_into_employee"),
    ]

    operations = [
        migrations.RenameField(
            model_name="employee",
            old_name="badge_number",
            new_name="company_number",
        ),
    ]
