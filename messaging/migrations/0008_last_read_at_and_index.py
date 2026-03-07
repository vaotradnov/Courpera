from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0007_room_slowmode_expiry"),
    ]

    operations = [
        migrations.AddField(
            model_name="roommembership",
            name="last_read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="roommembership",
            index=models.Index(fields=["room", "user"], name="msg_mem_room_user_idx"),
        ),
    ]
