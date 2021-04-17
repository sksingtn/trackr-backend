from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from trackr.settings import AUTH_USER_MODEL as User
from datetime import date
from django.utils import timezone


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


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/admin/', default='default.jpg')

    def __str__(self):
        return f'{self.name} (ADMIN)'


class FacultyProfile(models.Model):
    """Initialize a user with unusable_password if invited and let them set a password
        upon accepting the Invite . If not invited then leave the user field empty
    """

    # Add the Email Invitation as a post_save trigger or in the serializer.

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE,related_name='invited_faculties')
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/faculty/',default='default.jpg')

    @property
    def status(self):
        if self.user:
            return 'VERIFIED' if self.user.has_usable_password() else 'INVITED'
        return 'UNVERIFIED'

    def __str__(self):
        return f'{self.name} (Invited by : {self.admin.name} | Status : {self.status})'


class StudentProfile(models.Model):
    #Currently a student can be connected to multiple batches 
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/student/', default='default.jpg')

    def __str__(self):
        return f'{self.name} (STUDENT)'


# Rename to Batch
class Schedule(models.Model):
    title = models.CharField(max_length=200)
    admin = models.ForeignKey(AdminProfile, on_delete=models.CASCADE)
    #What happens when disabled?
    active = models.BooleanField(default=True)

    students = models.ManyToManyField(StudentProfile,through="StudentData")
    created = models.DateField(default=date.today)

    def __str__(self):
        # More Detailed Representation
        return f'{self.title} ({self.connected_slots.all().count()} Slots Assigned)'


class StudentData(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    date_followed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.student.name} Followed {self.schedule.title} on {self.date_followed}'


#Rename to timing
class Slot(models.Model):
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

#Rename to slot
class SlotInfo(models.Model):
    schedule = models.ForeignKey(Schedule, related_name='connected_slots', on_delete=models.CASCADE)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        #Inside a batch, there should be no 2 classes happening at the same time
        #Maybe this is redundant because the serializers already detect overlapping classes in a batch
        unique_together = ['slot', 'schedule']

    def __str__(self):
        return f'{self.title} Taught By {self.faculty} ({self.slot})'
