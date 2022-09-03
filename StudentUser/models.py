import uuid

from django.db import models
from django.contrib.auth import get_user_model

from trackr import settings
from base.models import Activity, Batch


class StudentProfile(models.Model):
    """
    Students can join a batch by creating an account via
    the invite link shared by Admin.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=100)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True) 
    
    batch = models.ForeignKey(Batch,null=True,on_delete=models.SET_NULL,
            related_name="student_profiles",related_query_name='students')
    joined = models.DateField(auto_now_add=True)
    receive_email_notification = models.BooleanField(default=False)
    

    def __str__(self):
        return f'{self.name} (STUDENT)'

    def is_active(self):
        return self.batch is not None

    @classmethod
    def create_profile(cls, *, name, email, password, batch, receive_email_notification):
        CustomUser = get_user_model()
        user = CustomUser.objects.create_user(email,password,
                        user_type=CustomUser.STUDENT)

        studentProfile = cls.objects.create(user=user, name=name,batch=batch, 
                        receive_email_notification=receive_email_notification)
        
        Activity.objects.create(user=user,text="You Signed up with a Student Account.")
        #For Admin of the current student.
        Activity.objects.create(user=batch.admin.user,
        text=f"'{name}' signed up for a STUDENT Account in '{batch.title}' batch.")

        return studentProfile

