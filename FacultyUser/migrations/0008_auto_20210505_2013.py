# Generated by Django 2.2.17 on 2021-05-05 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FacultyUser', '0007_remove_facultyprofile_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facultyprofile',
            name='joined',
            field=models.DateField(blank=True, null=True),
        ),
    ]