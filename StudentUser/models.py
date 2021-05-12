from django.db import models

from trackr.settings import AUTH_USER_MODEL as User
from base.models import Batch


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) 
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/student/', default='default.jpg')

    #If none, then account deleted by admin.
    batch = models.ForeignKey(Batch,null=True,on_delete=models.SET_NULL,related_name="student_profiles")
    joined = models.DateField(auto_now_add=True)
    

    def __str__(self):
        return f'{self.name} (STUDENT)'

    def is_active(self):
        #To determine if account has been deleted by admin
        return self.batch is not None
