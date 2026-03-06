from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0006_delay_and_visibility"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="slow_mode_expires_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
