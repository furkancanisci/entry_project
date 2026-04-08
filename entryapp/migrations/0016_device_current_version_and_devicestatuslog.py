from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("entryapp", "0015_goal_deleted_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="current_version",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.CreateModel(
            name="DeviceStatusLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(max_length=255)),
                ("payload", models.JSONField(blank=True, null=True)),
                ("reported_version", models.CharField(blank=True, max_length=50, null=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_logs",
                        to="entryapp.device",
                    ),
                ),
            ],
            options={
                "ordering": ["-received_at"],
            },
        ),
    ]
