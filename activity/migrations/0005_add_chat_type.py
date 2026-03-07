from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0004_alter_notification_type"),
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
                    ("chat", "Chat"),
                ],
                max_length=20,
            ),
        ),
    ]
