from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0004_alter_attempt_submitted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="available_from",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
