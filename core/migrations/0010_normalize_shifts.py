from datetime import time
from decimal import Decimal

from django.db import migrations, models


SHIFT_DEFINITIONS = [
    ("Morning", "M", time(6, 0), time(14, 0), {"morning", "demo morning shift"}),
    ("Day", "D", time(8, 0), time(18, 0), {"day", "demo day shift"}),
    ("Evening", "E", time(14, 0), time(22, 0), {"evening", "demo evening shift"}),
    ("Night", "N", time(18, 0), time(6, 0), {"night", "demo night shift"}),
    ("Weekend", "W", time(9, 0), time(17, 0), {"weekend", "demo weekend shift"}),
]


def shift_matches(shift, start_time, end_time, aliases):
    return (
        shift.shift_name.strip().lower() in aliases
        or (shift.start_time == start_time and shift.end_time == end_time and "demo" in shift.shift_name.lower())
    )


def unique_code(base_code, used_codes):
    code = base_code[:10]
    if code not in used_codes:
        used_codes.add(code)
        return code
    suffix = 2
    while True:
        candidate = f"{base_code[: 10 - len(str(suffix))]}{suffix}"
        if candidate not in used_codes:
            used_codes.add(candidate)
            return candidate
        suffix += 1


def code_from_name(name):
    words = [word for word in name.replace("-", " ").split() if word]
    if not words:
        return "SHIFT"
    return "".join(word[0] for word in words).upper()[:10]


def duration_hours(start_time, end_time):
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    return Decimal(end_minutes - start_minutes) / Decimal(60)


def reassign_shift_references(apps, duplicate, canonical):
    Deployment = apps.get_model("core", "Deployment")
    GuardSchedule = apps.get_model("core", "GuardSchedule")
    Attendance = apps.get_model("core", "Attendance")
    ContractSiteRequirement = apps.get_model("core", "ContractSiteRequirement")

    Deployment.objects.filter(shift=duplicate).update(shift=canonical)
    GuardSchedule.objects.filter(shift=duplicate).update(shift=canonical)
    Attendance.objects.filter(shift=duplicate).update(shift=canonical)

    for requirement in ContractSiteRequirement.objects.filter(shift=duplicate):
        existing = ContractSiteRequirement.objects.filter(
            contract_id=requirement.contract_id,
            site_id=requirement.site_id,
            shift=canonical,
            start_date=requirement.start_date,
        ).first()
        if existing:
            requirement.delete()
        else:
            requirement.shift = canonical
            requirement.save(update_fields=["shift", "updated_at"])


def normalize_shifts(apps, schema_editor):
    Shift = apps.get_model("core", "Shift")

    for label, code, start_time, end_time, aliases in SHIFT_DEFINITIONS:
        matching = [shift for shift in Shift.objects.all() if shift_matches(shift, start_time, end_time, aliases)]
        if not matching:
            Shift.objects.create(
                shift_name=label,
                code=code,
                start_time=start_time,
                end_time=end_time,
                hours_per_shift=duration_hours(start_time, end_time),
                shift_type=code,
            )
            continue

        canonical = next((shift for shift in matching if shift.shift_name.strip().lower() == label.lower()), matching[0])
        canonical.shift_name = label
        canonical.code = code
        canonical.start_time = start_time
        canonical.end_time = end_time
        canonical.save(update_fields=["shift_name", "code", "start_time", "end_time", "updated_at"])

        for duplicate in matching:
            if duplicate.pk == canonical.pk:
                continue
            reassign_shift_references(apps, duplicate, canonical)
            duplicate.delete()

    used_codes = {code for code in Shift.objects.exclude(code__isnull=True).exclude(code="").values_list("code", flat=True)}
    used_names = set()
    for shift in Shift.objects.order_by("id"):
        name = shift.shift_name.strip() or f"Shift {shift.pk}"
        original_name = name
        suffix = 2
        while name.lower() in used_names:
            name = f"{original_name} {suffix}"
            suffix += 1
        used_names.add(name.lower())

        if not shift.code:
            shift.code = unique_code(code_from_name(name), used_codes)
        shift.shift_name = name
        shift.save(update_fields=["shift_name", "code", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_contract_contractsiterequirement"),
    ]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="code",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.RunPython(normalize_shifts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="shift",
            name="shift_name",
            field=models.CharField(max_length=80, unique=True),
        ),
        migrations.AlterField(
            model_name="shift",
            name="code",
            field=models.CharField(max_length=10, unique=True),
        ),
        migrations.RemoveField(
            model_name="shift",
            name="hours_per_shift",
        ),
        migrations.RemoveField(
            model_name="shift",
            name="shift_type",
        ),
    ]
