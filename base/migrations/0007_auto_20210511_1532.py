# Generated by Django 2.2.17 on 2021-05-11 10:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_customuser_user_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Broadcast',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read', models.BooleanField(default=False)),
                ('broadcast', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Broadcast')),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='broadcast',
            name='receivers',
            field=models.ManyToManyField(related_name='received_broadcasts', through='base.Message', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='broadcast',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_broadcasts', to=settings.AUTH_USER_MODEL),
        ),
    ]