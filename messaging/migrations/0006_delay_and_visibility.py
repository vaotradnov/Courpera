import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0005_attachments_presence_moderation"),
    ]

    operations = [
        migrations.AddField(
            model_name="roommembership",
            name="delay_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="message",
            name="visible_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="message",
            name="published_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["room", "visible_at"], name="msg_room_visible_idx"),
        ),
    ]
