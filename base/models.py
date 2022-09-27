import os
import uuid
from datetime import date,datetime,timedelta
from PIL import Image
from io import BytesIO

from django.db import models
from django.core.files import File
from django.db.models.signals import pre_save,post_save
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.authtoken.models import Token
from django_resized import ResizedImageField

from .managers import SlotManager,BatchManager
from .utils import get_elapsed_string
from trackr.settings import WEEKDAYS



class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    #TODO: Figure out if its called anywhere internally
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    #TODO: probably not needed
    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


def main_image_path(instance, filename):
    _,extension = os.path.splitext(filename)
    return f'profile_images/{instance.user_type}/main__{uuid.uuid4()}{extension}'

def thumbnail_path(instance,filename):
    return f'profile_images/{instance.user_type}/thumbnail/{filename}'


class CustomUser(AbstractUser):

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    username = None
    email = models.EmailField(unique=True)

    profile_image = ResizedImageField(
        size=[1080, 1350], quality=75, upload_to=main_image_path, null=True, blank=True)
    thumbnail = models.ImageField(upload_to=thumbnail_path, null=True, blank=True) 

    ADMIN = 'ADMIN'
    FACULTY = 'FACULTY'
    STUDENT = 'STUDENT'
    type_choices = ((ADMIN,ADMIN),
                    (FACULTY,FACULTY),
                    (STUDENT,STUDENT))

    user_type = models.CharField('User Profile Type',choices=type_choices,null=True,blank=True,max_length=10)

    objects = CustomUserManager()

    def __str__(self):
        return self.email


def generate_thumbnail(sender,instance,*args,**kwargs):
    #Only generate when new profile_image is uploaded.
    if instance.profile_image and not instance.profile_image.closed:
        _,extension = os.path.splitext(instance.profile_image.name)      
        img = Image.open(instance.profile_image)
        img.thumbnail((300,240))  
        
        thumb = BytesIO()  
        img.save(thumb,img.format)
        thumb_name = f'thumbnail_{uuid.uuid4()}{extension}'
        instance.thumbnail = File(thumb, name=thumb_name)

def create_auth_token(sender, instance=None, created=False, **kwargs):
    #To prevent Token generation for INVITED Faculty accounts.
    if created and instance.has_usable_password():
        Token.objects.create(user=instance)

pre_save.connect(generate_thumbnail, sender=CustomUser)
post_save.connect(create_auth_token,sender=CustomUser)


class Broadcast(models.Model):
    """
    1.Admin users can broadcast messages to their connected Faculty/Student users
      but can't receive broadcasts from anyone.
    2.Faculty users can broadcast messages to their connected Student users
      and can receive broadcasts from their admin.
    3.Student users can receive broadcasts from their Admin & connected faculties
      but cant send broadcasts to anyone.
    """
    PREVIEW_LENGTH = 80

    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_broadcasts')
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    receivers = models.ManyToManyField(CustomUser, through='Message',related_name='received_broadcasts')

    def preview_text(self):
        return f'"{self.text[:self.PREVIEW_LENGTH]}{".." if len(self.text) > self.PREVIEW_LENGTH else ""}"'

    def __str__(self):
        msg = f'{self.sender.email} sent {self.preview_text()} to {self.receivers.count()} people'
        return msg

    def save(self,*args,**kwargs):
        if self.text == "":
            raise DjangoValidationError('\'text\' field cant be empty!')
        if self.sender.user_type not in {CustomUser.ADMIN,CustomUser.FACULTY}:
            raise DjangoValidationError('Broadcast can be sent by ADMIN/FACULTY users only!')
        super().save(*args,**kwargs)

#Unique constraint maybe needed
class Message(models.Model):
    """
    Custom M2M table to accomodate read attribute for each received message.
    """
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE)
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)

    def __str__(self):
        msg = f'{self.receiver.email} received {self.broadcast.preview_text()} from {self.broadcast.sender.email}'
        return msg


class Activity(models.Model):
    """
    Activity Log that is automatically generated for all users.
    Generated By their own actions or via the actions of related users.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    text = models.TextField()
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.text} ({self.user.email})'

    @classmethod
    def bulk_create_from_queryset(cls,*,queryset,text):
        bulk_create = []
        for obj in queryset:
            assert hasattr(obj,'user'),'Queryset Object needs to have a user attribute'
            bulk_create.append(cls(user=obj.user,text=text))
        
        cls.objects.bulk_create(bulk_create)


class Batch(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4,unique=True)
    title = models.CharField(max_length=200)
    admin = models.ForeignKey('AdminUser.AdminProfile', on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    onboard_students = models.BooleanField(default=True)
    max_students = models.PositiveIntegerField(default=100)

    objects = BatchManager()

    def __str__(self):
        return f'{self.title} ({self.connected_slots.all().count()} Slots Assigned)'

    def total_classes(self):
        return self.connected_slots.count()

    def total_students(self):
        return self.student_profiles.count()

    def getAssignedFaculties(self):
        from FacultyUser.models import FacultyProfile
        #Faculty that teach atleast 1 or more Slots in the current batch
        return FacultyProfile.objects.filter(slots__batch=self).distinct()

    def delete_batch(self):
        allStudents = self.student_profiles.all()
        Activity.bulk_create_from_queryset(queryset=allStudents,
        text= "Your account has been deleted because the associated Batch has been deleted by the admin.")

        Activity.objects.create(user=self.admin.user,
        text=f"You have deleted the '{self.title}' Batch.")

        self.delete()


class Slot(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4,unique=True)
    title = models.CharField(max_length=100)
    weekdays = (       
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday")
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    weekday = models.IntegerField(choices=weekdays)
    batch = models.ForeignKey(Batch, related_name='connected_slots',
                            related_query_name='slots', on_delete=models.CASCADE)
    faculty = models.ForeignKey('FacultyUser.FacultyProfile',related_name='teaches_in',
                                    related_query_name='slots', on_delete=models.CASCADE)
    #TODO: remove auto_now
    last_modified = models.DateTimeField(auto_now=True)

    next_utc_occurence = models.DateTimeField(null=True) 

    objects = SlotManager()

    def __str__(self):
        return f'{self.title} Taught By {self.faculty} ({self.start_time} - {self.end_time} {self.weekday})'


    @classmethod
    def create_slot(cls,title,start_time,end_time,weekday,faculty,batch):

        possibleOverlaps = cls.objects.possible_overlap_queryset(weekday,faculty,batch)
        possibleOverlaps.detect_overlap(start_time,end_time,batch)

        return cls.objects.create(title=title,start_time=start_time,end_time=end_time,
                weekday=weekday,batch=batch,faculty=faculty)

    def update_slot(self,title,start_time,end_time,weekday,faculty):

        possibleOverlaps = Slot.objects.possible_overlap_queryset(weekday,faculty,self.batch)
        possibleOverlaps = possibleOverlaps.exclude(pk=self.id)

        possibleOverlaps.detect_overlap(start_time,end_time,self.batch)

        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.weekday = weekday
        self.faculty = faculty
        self.save()
        
    def get_weekday_string(self):
        return WEEKDAYS[self.weekday]

    def get_start_time(self):
        return self.start_time.strftime('%I:%M%p')

    def get_end_time(self):
        return self.end_time.strftime('%I:%M%p')

    def get_duration_in_seconds(self):
        commonDate = date(1999, 6, 21)
        startTime = datetime.combine(commonDate, self.start_time)
        endTime = datetime.combine(commonDate, self.end_time)
        return (endTime-startTime).total_seconds()

    def get_duration(self):
        total_seconds = self.get_duration_in_seconds()
        return f'{int(total_seconds//60)} Mins'

    def get_last_modified(self):
        return get_elapsed_string(self.last_modified)
