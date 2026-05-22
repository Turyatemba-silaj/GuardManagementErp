from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_alter_attendance_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="passport_photo",
            field=models.FileField(blank=True, upload_to="employee_passport_photos/"),
        ),
    ]
