from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0002_studentfilesubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="is_published",
            field=models.BooleanField(default=False),
        ),
    ]
