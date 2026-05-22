from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_employee_passport_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="next_of_keen",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="employee",
            name="next_of_keen_contact",
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
