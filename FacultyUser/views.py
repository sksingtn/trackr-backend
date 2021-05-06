
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework import status
from django.utils import timezone


from .serializers import (FacultySlotSerializer,PreviousSlotSerializer,
                            OngoingSlotSerializer,NextSlotSerializer,
                          InviteTokenVerifySerializer,FacultyPasswordSerializer)
from .permissions import IsFaculty
from base.models import Slot

class CreateAccountView(APIView):
    permission_classes = [AllowAny]
    
    def get(self,request):
        """
        Verfies token and sends data to be displayed to frontend so that 
        faculty can be onboarded.
        """
        data = InviteTokenVerifySerializer(data=request.query_params)
        data.is_valid(raise_exception=True)

        target_user = data.save()
        user_info = {'name':target_user.name,'invited_by':target_user.admin.name,
                    'email':target_user.user.email}
        return Response({'status':1,'data':user_info},status=status.HTTP_200_OK)

    def post(self,request):
        password = FacultyPasswordSerializer(data=request.data)
        password.is_valid(raise_exception=True)
        password = password.validated_data['password']

        data = InviteTokenVerifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        new_user =  data.save(password=password)
        assert new_user.status == new_user.VERIFIED
        return Response({'status': 1, 'data': 'Faculty Account created successfully, login to continue.'}, status=status.HTTP_201_CREATED)
    
class TimelineView(APIView):

    permission_classes = [IsAuthenticated, IsFaculty]
    #Make a common class for both faculty and student view.
    def get(self,request):

        if not self.request.profile.is_active():
            raise ValidationError('Your Account has been deleted by the admin!')
            
        admin = request.profile.admin
        if not admin.active:
            raise ValidationError('Admin has paused the classes for all batches!')
      
        currentDateTime = timezone.localtime()
        all_slots = Slot.objects.filter(faculty=request.profile,batch__active=True).select_related(
            'timing', 'batch')

        if not all_slots:
            raise ValidationError('No classes Found! , Either classes are not assigned or paused!')
       
        previousSlot, ongoingSlot, nextSlot = all_slots.find_previous_ongoing_next_slot(currentDateTime=currentDateTime)

        timelineData = {}
        context = {'currentDateTime': currentDateTime}
        for slot, serializer in ((previousSlot, PreviousSlotSerializer),
                                (ongoingSlot, OngoingSlotSerializer),
                                (nextSlot, NextSlotSerializer)):

            fieldName = serializer.__name__.replace('Serializer','')
            value = None
            if slot is not None:
                value = serializer(slot,context=context).data
            
            timelineData[fieldName] = value

        jsonData = all_slots.order_by('timing__start_time').serialize_and_group_by_weekday(
                    serializer=FacultySlotSerializer)

        return Response({'timelineData':timelineData,'weekdayData': jsonData},status=status.HTTP_200_OK)
