# Generated by Django 2.2.17 on 2021-05-14 13:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0008_activity'),
    ]

    operations = [
        migrations.RenameField(
            model_name='activity',
            old_name='message',
            new_name='text',
        ),
    ]