from django.db import models
from django.utils import timezone
from django.core import signing


from trackr.settings import AUTH_USER_MODEL as User
from AdminUser.models import AdminProfile
from .exception import Error


class FacultyProfile(models.Model):
    """Initialize a user with unusable_password if invited and let them set a password
        upon accepting the Invite . If not invited then leave the user field empty
    """
    VERIFIED = 'VERIFIED'
    INVITED = 'INVITED'
    UNVERIFIED = 'UNVERIFIED'
    
    # Add the Email Invitation as a post_save trigger or in the serializer.
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    admin = models.ForeignKey(AdminProfile,null=True, on_delete=models.CASCADE,related_name='invited_faculties')
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='profile_images/faculty/',default='default.jpg')
    joined = models.DateField(null=True,blank=True)
    invite_sent = models.DateField(null=True)

    @property
    def status(self):
        if self.user:
            return self.VERIFIED if self.user.has_usable_password() else self.INVITED
        return self.UNVERIFIED

    def __str__(self):
        if not self.is_active():
            return f'{self.name} (DELETED)'
        return f'{self.name} (Invited by : {self.admin.name} | Status : {self.status})'
    
    def is_active(self):
        #To determine if account has been deleted by admin
        return self.admin is not None

    @staticmethod
    def _initialize_user(email):
        from base.models import CustomUser
        new_user = CustomUser(email=email)
        new_user.set_unusable_password()
        new_user.full_clean()
        new_user.save()
        return new_user

    def send_invite(self):
        """ 
        Sends an email Invite to the email of this faculty,
        Used to resend invites as well as to send the initital invite.
        """
        currentStatus = self.status
        if currentStatus != self.INVITED:
            if currentStatus == self.UNVERIFIED:
                raise Error('Profile does not have an email!')
            elif currentStatus == self.VERIFIED:
                raise Error('Profile is already verified!')

        currentDate = timezone.localtime().date()
        if currentDate == self.invite_sent:
            raise Error('You have already sent an invite today!')

        #send_email(self.name,self.user.email)
        token = signing.dumps({'email':self.user.email,'invited_by':str(self.admin.uuid)})

        temp = open('email.log','a')
        print(f'\nEmail sent to {self.user.email} with token \n {token}\n',file=temp)
        temp.close()

        self.invite_sent = currentDate
        self.save()

    
    def add_user(self,*,email):
        """
        Adds a user to a profile and sends an invite to their email,
        or override existing Invited user with a new user and sends an invite email
        if profile was initially created without a user.
        """
        currentStatus = self.status
        if currentStatus == self.VERIFIED:
            raise Error('Profile already has a Verified User!')

        if currentStatus == self.INVITED:
            self.invite_sent = None
        
        new_user = self._initialize_user(email)
        self.user = new_user
        self.save()
        self.send_invite()

    @classmethod
    def create_profile(cls,name,admin,email=False):
        profile = cls(admin=admin,name=name)
        
        if email:
            new_user = cls._initialize_user(email)
            profile.user = new_user
        
        profile.save()

        if profile.status == profile.INVITED:
            profile.send_invite()
        
        return profile

        #Replace with this after verifying test cases
        """
        profile = cls(admin=admin, name=name)
        profile.save()

        if email:
            profile.add_user(email)

        return profile
        """


         
    def delete_preview(self):
        #can prefetch_related be used?
        all_slots = self.slot_set.select_related('batch', 'timing').order_by('batch')
        delete_preview = []
        for slot in all_slots:
            preview_text = (f'{slot.title} in {slot.batch.title} on {slot.timing.get_weekday_string()}'
                            f'({slot.timing.get_start_time()}-{slot.timing.get_end_time()})')
            delete_preview.append(preview_text)
        return delete_preview

    def delete_profile(self):
        """
        Delete Slots taught by this faculty.
        If faculty was onboarded to the platform then preserve the FacultyProfile,
        otherwise delete the profile.        
        """
        deleted_slot_count ,_ = self.slot_set.all().delete()
        if self.status == self.VERIFIED:
            self.admin = None
            self.save()
        else:
            self.delete()
        return deleted_slot_count
