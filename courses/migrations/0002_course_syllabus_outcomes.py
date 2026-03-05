from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="syllabus",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="course",
            name="outcomes",
            field=models.TextField(blank=True),
        ),
    ]
