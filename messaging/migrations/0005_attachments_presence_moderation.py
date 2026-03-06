from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import messaging.models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0004_message_thread_softdelete_reaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="slow_mode_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="roommembership",
            name="muted_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roommembership",
            name="banned",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="Attachment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to="chat/", validators=[messaging.models.validate_chat_upload]
                    ),
                ),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("mime", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="messaging.message",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="attachment",
            index=models.Index(fields=["message", "created_at"], name="msg_attach_msg_created_idx"),
        ),
        migrations.CreateModel(
            name="Report",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("reason", models.CharField(max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("resolved", "Resolved"),
                            ("dismissed", "Dismissed"),
                        ],
                        default="open",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "handled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reports_handled",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="messaging.message",
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(
                fields=["status", "created_at"], name="msg_report_status_created_idx"
            ),
        ),
    ]
