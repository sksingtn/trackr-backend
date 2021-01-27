# Generated by Django 2.2.17 on 2021-01-25 06:16

import datetime
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_auto_20210124_1942'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='created',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AddField(
            model_name='slotinfo',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
