from django.db import migrations


def set_defaults_for_published(apps, schema_editor):
    Assignment = apps.get_model("assignments", "Assignment")
    from datetime import timedelta

    from django.utils import timezone

    now = timezone.now()
    for a in Assignment.objects.filter(is_published=True, available_from__isnull=True):
        a.available_from = now
        if a.deadline is None:
            a.deadline = a.available_from + timedelta(days=7)
        a.save(update_fields=["available_from", "deadline"])


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0005_assignment_available_from"),
    ]

    operations = [
        migrations.RunPython(set_defaults_for_published, migrations.RunPython.noop),
    ]
