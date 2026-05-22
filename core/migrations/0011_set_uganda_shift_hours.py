from datetime import time

from django.db import migrations


def set_uganda_shift_hours(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")
    Shift.objects.filter(code="D").update(start_time=time(8, 0), end_time=time(20, 0))
    Shift.objects.filter(code="N").update(start_time=time(18, 0), end_time=time(6, 0))


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_normalize_shifts"),
    ]

    operations = [
        migrations.RunPython(set_uganda_shift_hours, migrations.RunPython.noop),
    ]
