import uuid
from datetime import date,datetime,timedelta

from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models import Q

from AdminUser.models import AdminProfile
from FacultyUser.models import FacultyProfile
from .managers import SlotManager
from .utils import WEEKDAYS


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

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

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField('email address', unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Batch(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4,unique=True)
    title = models.CharField(max_length=200)
    admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created = models.DateField(default=date.today)

    onboard_students = models.BooleanField(default=True)
    max_students = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f'{self.title} ({self.connected_slots.all().count()} Slots Assigned)'

    
    def delete_preview(self):
        all_slots = self.connected_slots.select_related('faculty','timing').order_by('timing__weekday')
        slot_delete_preview = []
        for slot in all_slots:
            preview_text = (f'{slot.title} taught by {slot.faculty.name} on {slot.timing.get_weekday_string()}'
                            f'({slot.timing.get_start_time()}-{slot.timing.get_end_time()})')
            slot_delete_preview.append(preview_text)

        all_students = self.student_profiles.select_related('user').order_by('name')
        student_delete_preview = []
        for student in all_students:
            preview_text = f'{student.name} ({student.user.email})'
            student_delete_preview.append(preview_text)

        return {'slot_preview':slot_delete_preview,'student_preview':student_delete_preview}

    def delete_batch(self):
        
        pass


class Timing(models.Model):
    """This is not attached to a user to ease the notifier function,
        because this way we can query for an incoming slot and it will give us
        details for upcoming classes of every batch of every user"""
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


    def __str__(self):
        return f'{self.start_time} - {self.end_time} ({self.weekday})'

    def get_weekday_string(self):
        return WEEKDAYS[self.weekday]

    def get_start_time(self):
        return self.start_time.strftime('%I:%M %p')

    def get_end_time(self):
        return self.end_time.strftime('%I:%M %p')
  
    def get_duration_in_seconds(self):
        #Cant subtract time from time so combined both with a common date.
        commonDate = date(1999, 6, 21)
        startTime = datetime.combine(commonDate, self.start_time)
        endTime = datetime.combine(commonDate, self.end_time)
        return (endTime-startTime).total_seconds()

    def get_duration(self):
        total_seconds = self.get_duration_in_seconds()
        return f'{int(total_seconds//60)} Mins'

    def get_elapsed_seconds(self,currentDateTime):
        currentDateTime = currentDateTime.replace(tzinfo=None)
        slotStartTime = datetime.combine(currentDateTime.date(),self.start_time)
        slotEndTime = datetime.combine(currentDateTime.date(),self.end_time)

        if currentDateTime.weekday() != self.weekday or (not slotStartTime <= currentDateTime <= slotEndTime):
            raise Exception('Slot does not coincide with current time!')

        elapsedSeconds = (currentDateTime - slotStartTime).total_seconds()

        return int(elapsedSeconds)

    def get_elapsed(self, currentDateTime):
        currentDateTime = currentDateTime.replace(tzinfo=None)
        currentDate = currentDateTime.date()

        dayOffset = self.weekday - currentDateTime.weekday()
        buildDate = currentDate + timedelta(days=dayOffset)

        if dayOffset < 0 or (dayOffset == 0 and datetime.combine(currentDate,self.end_time) < currentDateTime):
            time = self.end_time
        elif dayOffset > 0 or (dayOffset == 0 and datetime.combine(currentDate,self.start_time) > currentDateTime):
            time = self.start_time
        else:
            raise Exception('Slot coincides with current time!')

        buildDateTime = datetime.combine(buildDate,time)

        total_seconds = (currentDateTime-buildDateTime).total_seconds()

        return int(abs(total_seconds))


#Add a last notified field (what to do with it in update?)
class Slot(models.Model):
    batch = models.ForeignKey(Batch, related_name='connected_slots', on_delete=models.CASCADE)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE)
    timing = models.ForeignKey(Timing, on_delete=models.CASCADE) # models.PROTECT
    title = models.CharField(max_length=100)
    #Rename to last_activity
    created = models.DateTimeField(default=timezone.localtime)

    objects = SlotManager()


    def get_last_activity(self):
        difference = (timezone.localtime()-self.created)
        total_seconds = difference.total_seconds()

        if difference.days:
            value = f"{difference.days} day{'s' if difference.days > 1 else ''}"
        elif total_seconds//3600:
            hours = total_seconds//3600
            value = f"{int(hours)} hour{'s' if hours > 1 else ''}"
        elif total_seconds//60:
            minutes = total_seconds//60
            value = f"{int(minutes)} minute{'s' if minutes > 1 else ''}"
        else:
            value = f'{int(total_seconds)} seconds'

        return f'{value} ago'

    def __str__(self):
        return f'{self.title} Taught By {self.faculty} ({self.timing})'

