from django.db import migrations, models


def backfill_attempts_policy(apps, schema_editor):
    Assignment = apps.get_model("assignments", "Assignment")
    # Default everything to 'latest', then set quizzes to 'best'
    Assignment.objects.filter().update(attempts_policy="latest")
    Assignment.objects.filter(type="quiz").update(attempts_policy="best")


class Migration(migrations.Migration):
    dependencies = [
        (
            "assignments",
            "0008_rename_assign_grd_asg_stu_idx_assignments_assignm_81964c_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="attempts_policy",
            field=models.CharField(
                choices=[("best", "Best"), ("latest", "Latest")], default="latest", max_length=10
            ),
        ),
        migrations.AddField(
            model_name="quizanswerchoice",
            name="explanation",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(backfill_attempts_policy, migrations.RunPython.noop),
    ]
