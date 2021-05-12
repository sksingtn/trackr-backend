from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist



WEEKDAYS = ['Monday', 'Tuesday','Wednesday', 'Thursday', 'Friday', 'Saturday','Sunday']

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
                #For Field Specific Errors include the field name too.
                new_response['data'] = f'{errorField} => {str(errorDetail[0])}'
        
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
