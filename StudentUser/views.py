from StudentUser.models import StudentProfile
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework import status

from .serializers import (StudentSlotSerializer, PreviousSlotSerializer,
                          OngoingSlotSerializer, NextSlotSerializer,
                          InviteLinkVerifySerializer, StudentSignupSerializer)
from base.permissions import IsAuthenticatedWithProfile


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

        #Use is_active()
        if batch is None:
            raise ValidationError('Your Account has been deleted by the admin!')

        if not batch.admin.active:
            raise ValidationError('Admin has paused the classes for all batches!')

        if not batch.active:
            raise ValidationError('Admin has paused the classes for this batch!')

        currentDateTime = timezone.localtime()
        all_slots = request.profile.batch.connected_slots.select_related(
            'timing', 'faculty')

        if not all_slots:
            raise ValidationError('No classes assigned by the Admin yet!')

        previousSlot, ongoingSlot, nextSlot = all_slots.find_previous_ongoing_next_slot(
            currentDateTime=currentDateTime)

        timelineData = {}
        context = {'currentDateTime': currentDateTime}
        for slot, serializer in ((previousSlot, PreviousSlotSerializer),
                                 (ongoingSlot, OngoingSlotSerializer),
                                 (nextSlot, NextSlotSerializer)):

            fieldName = serializer.__name__.replace('Serializer', '')
            value = None
            if slot is not None:
                value = serializer(slot, context=context).data

            timelineData[fieldName] = value

        jsonData = all_slots.order_by('timing__start_time').serialize_and_group_by_weekday(
            serializer=StudentSlotSerializer)

        return Response({ 'status':1 , 'data':{'timelineData': timelineData, 'weekdayData': jsonData}}, status=status.HTTP_200_OK)
