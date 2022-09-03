import uuid

from django.db import models
from django.utils import timezone
from django.core import signing
from django.db.models.signals import pre_save
from django.contrib.auth.models import BaseUserManager

from rest_framework.authtoken.models import Token

from trackr.settings import AUTH_USER_MODEL as User
from AdminUser.models import AdminProfile
from .exception import Error
from base.models import CustomUser,Batch,Activity
from base.utils import get_image




class FacultyProfile(models.Model):
    """
    Profile can have following 3 states
     1.UNVERIFIED : Profile doesn't have a user instance which means 
     admin created this profile without specifying an email.

     2.INVITED : Profile has a blank user instance i.e with unusable password which means
     admin has specified an email for this profile and an invitation mail has been sent,
     but the recipient hasn't accepted the invite yet.

     3.VERIFIED : Profile has a usable user instance which means the recipient has
     accepted the email invite and has claimed the profile.

    """
   
    #TODO: What happens to sent broadcasts on delete?

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    admin = models.ForeignKey(AdminProfile,null=True, on_delete=models.CASCADE,related_name='connected_faculties')
    
    UNVERIFIED = 'UNVERIFIED'
    INVITED = 'INVITED'
    VERIFIED = 'VERIFIED'
    status_choices = ((VERIFIED,VERIFIED),(INVITED,INVITED),(UNVERIFIED,UNVERIFIED))
    status = models.CharField(max_length=100,choices=status_choices,null=True,blank=True)

    added = models.DateTimeField(auto_now_add=True)
    joined = models.DateTimeField(null=True,blank=True)
    invite_sent = models.DateTimeField(null=True,blank=True)

    receive_email_notification = models.BooleanField(default=False)


    def __str__(self):
        if not self.is_active():
            return f'{self.name} (DELETED)'
        return f'{self.name} (Invited by : {self.admin.name} | Status : {self.status})'
    
    def is_active(self):
        return self.admin is not None

    def get_current_status(self):
        if self.user:
            return self.VERIFIED if self.user.has_usable_password() else self.INVITED
        return self.UNVERIFIED

    def get_profile_image(self,request,thumbnail=True):
        if self.status == FacultyProfile.VERIFIED:       
            image = self.user.thumbnail if thumbnail else self.user.profile_image
            return get_image(request,image)
        return None

    @staticmethod
    def _initialize_user(email):      
        email = BaseUserManager.normalize_email(email)
        new_user = CustomUser(email=email,user_type=CustomUser.FACULTY)
        new_user.set_unusable_password()
        new_user.full_clean()
        new_user.save()
        return new_user
       
    @classmethod
    def create_profile(cls,*,name,admin,email=None):
        profile = cls(admin=admin, name=name)
        profile.save()

        if email is not None:
            profile.add_or_overwrite_user(email=email)

        Activity.objects.create(user=admin.user,
        text=f"You added '{name}' as faculty and invited them to create a FACULTY Account with {email}"
             if email is not None else f"You added '{name}' as faculty")
        
        return profile

    def send_invite(self,force_send=False):
        """ 
        Sends an email Invite to the email of this faculty,
        limited to 1/24 hrs unless force_send=True
        """
        currentStatus = self.status   
        if currentStatus == self.UNVERIFIED:
            raise Error('Profile does not have an email!')
        elif currentStatus == self.VERIFIED:
            raise Error('Profile is already verified!')

        currentDateTime = timezone.now()
        if not force_send and self.invite_sent is not None:
            hrs_elapsed = (currentDateTime - self.invite_sent).total_seconds() // 3600
            if hrs_elapsed < 24:
                raise Error('You have already sent an invite in last 24 hours!')
        
        token = signing.dumps({'email':self.user.email,'invitedBy':str(self.admin.uuid)})
        temp = open('email.log','a')
        temp.write(f'\nEmail sent to {self.user.email} with token \n {token}\n')
        temp.close()

        self.invite_sent = currentDateTime
        self.save()
    
    def add_or_overwrite_user(self,*,email):
        """
        If profile is UNVERIFIED then it adds an email to it,
        or if profile is INVITED then it will overwrite the old email
        ,and then it sends an email invite in both cases.
        """
        currentStatus = self.status
        if currentStatus == self.VERIFIED:
            raise Error('Profile already has a Verified User!')

        if currentStatus == self.INVITED:
            oldEmail = self.user.email
            if oldEmail == email:
                raise Error('New Email is same as old email!')
            self.user.delete()

            Activity.objects.create(user=self.admin.user,
            text=f"You changed the invite email from {oldEmail} to {email} for '{self.name}' Faculty Account")

            
        new_user = self._initialize_user(email)
        self.user = new_user
        self.save()
        self.send_invite(force_send = currentStatus==self.INVITED)

    def claim_account(self, *, password, receive_email_notification):
        if self.status == self.INVITED:
            self.user.set_password(password)
            self.user.save()
            self.joined = timezone.now()
            self.receive_email_notification = receive_email_notification
            self.save()

            #Because automatic Token generation is disabled for Faculty accounts
            #To make sure token is only generated for VERIFIED Accounts.
            Token.objects.create(user=self.user)

            #For Faculty User
            Activity.objects.create(user=self.user,text="You Signed up with a Faculty Account.")
            #For Admin of the current faculty
            Activity.objects.create(user=self.admin.user,
                                    text=f"{self.name} accepted you Invite for a Faculty account.")

        else:
            raise Error('Only Invited Users can claim their accounts!')

     
    def delete_profile(self):
        """
        If faculty was onboarded to the platform then preserve the FacultyProfile,
        so they can see what happened in the activity section,
        otherwise delete the profile.        
        """
        Activity.objects.create(user=self.admin.user,
        text=f"You deleted '{self.name}' ({self.status}) Faculty Account!")
         
        if self.status == self.VERIFIED:
            Activity.objects.create(user=self.user,text="Your Account has been deleted by Admin!")
            #Need to manually delete slots because cascading wont happen in this case.
            self.teaches_in.all().delete()
            self.admin = None
            self.save()
        else:
            #Slots that this faculty taught in will automatically get deleted via cascading.
            if self.status == self.INVITED:
                self.user.delete()
            self.delete()
        
    def assignedBatches(self):
        return Batch.objects.filter(slots__faculty=self).distinct()


def populate_faculty_status(sender,instance,*args,**kwargs):
    instance.status = instance.get_current_status()

pre_save.connect(populate_faculty_status,sender=FacultyProfile)
