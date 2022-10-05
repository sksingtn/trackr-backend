
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework import status

from .serializers import (OngoingSlotSerializer, NextOrPreviousSlotSerializer,
                          InviteLinkVerifySerializer, StudentSignupSerializer)
from base.serializers import StudentSlotDisplaySerializer
from base.permissions import IsAuthenticatedWithProfile
from base.utils import get_weekday
from StudentUser.models import StudentProfile


#TODO: Figure out how to verify email!
class CreateAccountView(APIView):
    """
    Student signup using a batch Invite link.
    """
    permission_classes = [AllowAny]
    serializer_class = StudentSignupSerializer
    
    def get(self,request):
        """
        Verfies token and sends token context data.
        Used to populate the Student signup form in frontend.
        """
        data = InviteLinkVerifySerializer(data=self.request.query_params)
        data.is_valid(raise_exception=True)
        targetBatch = data.save()
        
        inviteInfo = {'batch': targetBatch.title,
                      'admin': targetBatch.admin.name}
        return Response({'status': 1, 'data': inviteInfo}, status=status.HTTP_200_OK)

    def post(self,request):
        """
        After verifying the token,
        Student account is created with given details.
        """
        studentAccount = StudentSignupSerializer(data=request.data)
        studentAccount.is_valid(raise_exception=True)
        
        token = {'token': studentAccount.validated_data.pop('token')}
        token = InviteLinkVerifySerializer(data=token)
        token.is_valid(raise_exception=True)
        targetBatch = token.save()
        
        studentAccount.save(batch=targetBatch)       
        return Response({'status':1,'data':'Student Account created successfully, login to continue.'},
                        status=status.HTTP_201_CREATED)



class TimelineView(APIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = StudentProfile
    required_account_active = True

    def get(self, request):
        batch = request.profile.batch

        if not batch.active:
            raise ValidationError('Admin has paused the classes for this batch!')

        all_slots = request.profile.batch.connected_slots.select_related('faculty')

        if not all_slots:
            raise ValidationError('No classes assigned by the Admin yet!')

        tz = batch.admin.timezone
        timelineInfo = all_slots.find_previous_ongoing_next_slot(tz=tz,
                            pSerializer=NextOrPreviousSlotSerializer
                            ,oSerializer=OngoingSlotSerializer
                            ,nSerializer=NextOrPreviousSlotSerializer)

        jsonData = all_slots.order_by('start_time')\
                    .serialize_and_group_by_weekday(serializer=StudentSlotDisplaySerializer
                                                    ,context={"request":request})

        return Response({ 'status':1 , 
                          'data':{'timelineData': timelineInfo,
                                  'currentWeekday':get_weekday(tz),
                                  'weekdayData': jsonData}}, 
                        status=status.HTTP_200_OK)
