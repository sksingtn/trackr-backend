# Generated by Django 2.2.17 on 2021-05-05 14:01

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('FacultyUser', '0005_auto_20210505_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='facultyprofile',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
