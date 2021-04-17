from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from pprint import pprint


WEEKDAYS = ['Sunday', 'Monday', 'Tuesday','Wednesday', 'Thursday', 'Friday', 'Saturday']

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
