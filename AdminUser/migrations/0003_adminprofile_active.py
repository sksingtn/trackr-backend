# Generated by Django 2.2.17 on 2021-04-25 16:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AdminUser', '0002_adminprofile_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='adminprofile',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
