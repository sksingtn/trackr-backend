# Generated by Django 2.2.17 on 2021-05-06 10:27

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_auto_20210425_2225'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='max_students',
            field=models.PositiveIntegerField(default=100),
        ),
        migrations.AddField(
            model_name='batch',
            name='onboard_students',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='batch',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
