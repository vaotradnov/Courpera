from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0006_rename_course_subj_lvl_lang_idx_courses_cou_subject_47c6e5_idx_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="feedback",
            index=models.Index(fields=["created_at"], name="courses_fee_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="feedback",
            constraint=models.CheckConstraint(
                condition=models.Q(("rating__gte", 1)) & models.Q(("rating__lte", 5)),
                name="feedback_rating_range",
            ),
        ),
    ]
