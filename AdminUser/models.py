import uuid

from django.db import models
from django.contrib.auth import get_user_model

from timezone_field import TimeZoneField

from trackr import settings


class AdminProfile(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4,unique=True)
    name = models.CharField(max_length=100)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)   
    timezone = TimeZoneField()
    joined = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} (ADMIN)'

    @classmethod
    def create_profile(cls,*,name,email,password,timezone):
        from base.models import Activity
        CustomUser = get_user_model()
        user = CustomUser.objects.create_user(email,password,
                        user_type=CustomUser.ADMIN)

        adminProfile = cls.objects.create(name=name,user=user,timezone=timezone)
        Activity.objects.create(user=user,text='You Signed up with an ADMIN Account.')
        return adminProfile


