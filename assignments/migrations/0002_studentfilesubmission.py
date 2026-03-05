import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentFileSubmission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("file", models.FileField(upload_to="assignment_submissions/")),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="file_submissions",
                        to="assignments.attempt",
                    ),
                ),
            ],
        ),
    ]
