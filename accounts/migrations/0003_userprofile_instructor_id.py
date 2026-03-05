from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_userprofile_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="instructor_id",
            field=models.CharField(blank=True, null=True, unique=True, max_length=16),
        ),
    ]
