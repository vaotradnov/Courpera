import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assignments", "0006_backfill_published_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="max_marks",
            field=models.FloatField(default=100.0),
        ),
        migrations.AddField(
            model_name="attempt",
            name="marks_awarded",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attempt",
            name="graded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="graded_attempts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="attempt",
            name="graded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attempt",
            name="feedback_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="attempt",
            name="override_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="attempt",
            name="released",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="attempt",
            name="released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Grade",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("achieved_marks", models.FloatField(default=0.0)),
                ("max_marks", models.FloatField(default=100.0)),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grades",
                        to="assignments.assignment",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grades",
                        to="courses.course",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grades",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "attempt",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="grade_records",
                        to="assignments.attempt",
                    ),
                ),
            ],
            options={
                "unique_together": {("assignment", "student")},
            },
        ),
        migrations.AddIndex(
            model_name="grade",
            index=models.Index(fields=["assignment", "student"], name="assign_grd_asg_stu_idx"),
        ),
        migrations.AddIndex(
            model_name="grade",
            index=models.Index(fields=["course", "student"], name="assign_grd_crs_stu_idx"),
        ),
    ]
