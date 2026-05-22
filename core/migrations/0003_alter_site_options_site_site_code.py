import re

from django.db import migrations, models


def client_code_prefix(client_name):
    words = re.findall(r"[A-Za-z0-9]+", client_name.upper())
    if not words:
        return "CLNT"
    if len(words) == 1:
        return words[0][:4].ljust(4, "X")
    return "".join(word[0] for word in words)[:4].ljust(4, "X")


def populate_site_codes(apps, schema_editor):
    Site = apps.get_model("core", "Site")
    counters = {}
    for site in Site.objects.select_related("client").order_by("client_id", "id"):
        if site.site_code:
            continue
        prefix = client_code_prefix(site.client.client_name)
        key = (site.client_id, prefix)
        counters[key] = counters.get(key, 0) + 1
        site.site_code = f"{prefix}S{counters[key]:04d}"
        site.save(update_fields=["site_code"])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_guardschedule_attendance_schedule'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='site',
            options={'ordering': ['client__client_name', 'site_code', 'site_name']},
        ),
        migrations.AddField(
            model_name='site',
            name='site_code',
            field=models.CharField(blank=True, editable=False, max_length=20, null=True, unique=True),
        ),
        migrations.RunPython(populate_site_codes, migrations.RunPython.noop),
    ]
