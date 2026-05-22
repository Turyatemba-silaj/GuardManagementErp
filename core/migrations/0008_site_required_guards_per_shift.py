from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_guardschedule_replacement"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="required_guards_per_shift",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Contracted guard requirement per shift. Use 0 when not configured.",
            ),
        ),
    ]
