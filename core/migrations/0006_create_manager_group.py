from django.db import migrations


def create_manager_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Manager")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_attendance_shift"),
    ]

    operations = [
        migrations.RunPython(create_manager_group, migrations.RunPython.noop),
    ]
