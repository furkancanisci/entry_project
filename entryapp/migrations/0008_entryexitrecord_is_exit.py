# Generated by Django 5.1.7 on 2025-04-16 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entryapp', '0007_userpermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='entryexitrecord',
            name='is_exit',
            field=models.BooleanField(default=True),
        ),
    ]
