from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_userprofile_instructor_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="secret_word_hash",
            field=models.CharField(max_length=128, blank=True),
        ),
    ]
