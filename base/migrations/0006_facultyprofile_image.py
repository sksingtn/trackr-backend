# Generated by Django 2.2.17 on 2021-01-27 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_auto_20210125_0616'),
    ]

    operations = [
        migrations.AddField(
            model_name='facultyprofile',
            name='image',
            field=models.ImageField(default='default.jpg', upload_to='profile_images/faculty/'),
        ),
    ]
