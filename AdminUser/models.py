import uuid

from django.db import models

from trackr.settings import AUTH_USER_MODEL as User

class AdminProfile(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4,unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/admin/', default='default.jpg')

    active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.name} (ADMIN)'
