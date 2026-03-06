import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "assignments",
            "0011_rename_asmt_course_pub_deadline_idx_assignments_course__333906_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="grade",
            constraint=models.CheckConstraint(
                condition=models.Q(("achieved_marks__gte", 0.0))
                & models.Q(("max_marks__gte", 0.0)),
                name="grade_marks_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="grade",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("achieved_marks__lte", django.db.models.expressions.F("max_marks"))
                ),
                name="grade_marks_le_max",
            ),
        ),
    ]
