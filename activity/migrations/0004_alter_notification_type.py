from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0003_alter_notification_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("enrolment", "Enrolment"),
                    ("material", "Material"),
                    ("grade", "Grade"),
                    ("qna", "Q&A"),
                ],
                max_length=20,
            ),
        ),
    ]
