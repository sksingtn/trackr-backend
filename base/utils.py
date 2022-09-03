from datetime import date,datetime

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import MinimumLengthValidator

from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.

    response = exception_handler(exc, context)

    if response is not None and isinstance(exc, ValidationError):
        new_response = {"status":0,"data":""}
        #Only One Error Should be shown if muliple are there
        if isinstance(response.data,dict):
            #For Handling Validation Errors thrown directly from serializers
            errorField, errorDetail = response.data.popitem()
            if type(errorDetail) == dict:
                #For handling error response thrown from a nested serializer
                errorField, errorDetail = errorDetail.popitem()
        
            if errorField == 'error':
                new_response['data'] = errorDetail[0]
            else:
                #For some Field Specific Errors include the field name too.
                if str(errorDetail[0]) == 'This field is required.':
                    new_response['data'] = f'{errorField} => {str(errorDetail[0])}'
                else:
                    new_response['data'] = errorDetail[0]
        
        else:
            #For Handling Validation Errors thrown directly from views
            new_response['data'] = str(response.data[0])
        

        return Response(new_response, status=HTTP_400_BAD_REQUEST)

    return response


def get_elapsed_string(datetimeObj):
    difference = timezone.localtime()-datetimeObj
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


def get_user_profile(user):
    from AdminUser.models import AdminProfile
    from FacultyUser.models import FacultyProfile
    from StudentUser.models import StudentProfile

    user_type = user.user_type
    try:
        if user_type == user.ADMIN:
            profile = AdminProfile.objects.get(user=user)
        elif user_type == user.FACULTY:
            profile = FacultyProfile.objects.get(user=user)
        elif user_type == user.STUDENT:
            profile = StudentProfile.objects.get(user=user)
        else:
            raise ObjectDoesNotExist

    except ObjectDoesNotExist:            
        return None

    return profile

def unique_email_validator(email):
    from base.models import CustomUser

    if CustomUser.objects.filter(email=email).exists():
        raise ValidationError('User with this email already exists!')


class PasswordMinLengthValidator(MinimumLengthValidator):
    """
    Modified Django's validator to work with DRF
    """
    def __call__(self, password):
        try:
            self.validate(password)
        except DjangoValidationError:
            raise ValidationError(
                f'Password must be {self.min_length} characters long!')

        return password


def get_image(request,image):
    return (request.build_absolute_uri(image.url) 
            if bool(image) else None)

#TODO: can this be used in more places?
def get_time_difference(time1,time2):
    commonDate = date.today()
    time1 = datetime.combine(commonDate,time1)
    time2 = datetime.combine(commonDate,time2)
    return (time1 - time2).total_seconds()
    



