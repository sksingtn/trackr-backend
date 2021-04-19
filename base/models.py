from datetime import date

from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

from AdminUser.models import AdminProfile
from FacultyUser.models import FacultyProfile


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
    title = models.CharField(max_length=200)
    admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE)
    #What happens when disabled?
    active = models.BooleanField(default=True)
    created = models.DateField(default=date.today)

    def __str__(self):
        # More Detailed Representation
        return f'{self.title} ({self.connected_slots.all().count()} Slots Assigned)'


class Timing(models.Model):
    """This is not attached to a user to ease the notifier function,
        because this way we can query for an incoming slot and it will give us
        details for upcoming classes of every batch of every user"""
    weekdays = (
        ("Sunday", "Sunday"),
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday")
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    weekday = models.CharField(max_length=100, choices=weekdays)

    def __str__(self):
        return f'{self.start_time} - {self.end_time} ({self.weekday})'


#Add a last notified field (what to do with it in update?)
class Slot(models.Model):
    batch = models.ForeignKey(Batch, related_name='connected_slots', on_delete=models.CASCADE)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE)
    timing = models.ForeignKey(Timing, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    created = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return f'{self.title} Taught By {self.faculty} ({self.timing})'

    def get_start_time(self):
        return self.timing.start_time.strftime('%H:%M')

    def get_end_time(self):
        return self.timing.end_time.strftime('%H:%M')
