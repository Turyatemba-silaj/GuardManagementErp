import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_create_manager_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="guardschedule",
            name="replacement_guard",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replacement_schedules",
                to="core.guard",
            ),
        ),
        migrations.AddField(
            model_name="guardschedule",
            name="replacement_reason",
            field=models.TextField(blank=True),
        ),
    ]
