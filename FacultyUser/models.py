from django.db import models

from trackr.settings import AUTH_USER_MODEL as User
from AdminUser.models import AdminProfile

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
