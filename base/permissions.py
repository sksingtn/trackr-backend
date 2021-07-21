
from AdminUser.models import AdminProfile
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from StudentUser.models import StudentProfile
from FacultyUser.models import FacultyProfile

#TODO: Make sure all error messages have the uniform response structure.
class IsAuthenticatedWithProfile(IsAuthenticated):
    def has_permission(self, request, view):
        """
        1.Checks if user is authenticated.
        2.Checks if the authenticated user's profile matches the 
          specified 'required_profile' attribute on the view class,
          if profile is found then it is added to the request object.
        3.Checks if the found profile is active,only applicable to Student/Faculty (optional).
        """
        
        isAuth = super().has_permission(request, view)
    
        if not isAuth:   
            raise ValidationError('Authentication credentials were not provided!')

        assert hasattr(view,'required_profile'),\
        'required_profile attribute needs to be set on the view class'

        assert view.required_profile in {AdminProfile,FacultyProfile,StudentProfile},\
        'required_profile can only take AdminProfile/FacultyProfile/StudentProfile'

        try:
            profile = view.required_profile.objects.get(user=request.user)
        except ObjectDoesNotExist:
            raise ValidationError('Your account does not have permission to perform this action!')

        if view.required_profile in {FacultyProfile,StudentProfile}:
            if getattr(view, 'required_account_active', False) is True and (not profile.is_active()):
                raise ValidationError('Your Account has been deleted by the admin!')
            
        request.profile = profile
        return True



       


