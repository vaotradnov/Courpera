import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("courses", "0002_course_syllabus_outcomes"),
    ]

    operations = [
        migrations.CreateModel(
            name="Assignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("quiz", "Quiz"), ("paper", "Paper"), ("exam", "Exam")],
                        max_length=16,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("instructions", models.TextField(blank=True)),
                ("deadline", models.DateTimeField(blank=True, null=True)),
                ("attempts_allowed", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        migrations.CreateModel(
            name="Attempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("attempt_no", models.PositiveSmallIntegerField(default=1)),
                ("submitted_at", models.DateTimeField()),
                ("score", models.FloatField(blank=True, null=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="assignments.assignment",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.CreateModel(
            name="QuizQuestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("text", models.TextField()),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="assignments.assignment",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="QuizAnswerChoice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("text", models.CharField(max_length=500)),
                ("is_correct", models.BooleanField(default=False)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="assignments.quizquestion",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="StudentAnswer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="assignments.attempt",
                    ),
                ),
                (
                    "choice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="assignments.quizanswerchoice",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="assignments.quizquestion"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StudentTextAnswer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("text", models.TextField()),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="text_answers",
                        to="assignments.attempt",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="assignments.quizquestion"
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="studentanswer",
            unique_together={("attempt", "question")},
        ),
    ]
