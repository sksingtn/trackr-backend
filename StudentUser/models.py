from django.db import models

from trackr.settings import AUTH_USER_MODEL as User
from base.models import Batch

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/student/', default='default.jpg')
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name="student_profiles")

    def __str__(self):
        return f'{self.name} (STUDENT)'
