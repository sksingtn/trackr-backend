# Generated by Django 2.2.17 on 2021-05-06 14:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('StudentUser', '0004_studentprofile_joined'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprofile',
            name='batch',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_profiles', to='base.Batch'),
        ),
    ]
