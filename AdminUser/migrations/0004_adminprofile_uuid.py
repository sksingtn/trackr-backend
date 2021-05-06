# Generated by Django 2.2.17 on 2021-05-05 14:33

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('AdminUser', '0003_adminprofile_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='adminprofile',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]