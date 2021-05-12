# Generated by Django 2.2.17 on 2021-05-10 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_auto_20210506_1856'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='user_type',
            field=models.CharField(blank=True, choices=[('ADMIN', 'ADMIN'), ('FACULTY', 'FACULTY'), ('STUDENT', 'STUDENT')], max_length=10, null=True, verbose_name='User Profile Type'),
        ),
    ]
