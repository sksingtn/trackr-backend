
from django.utils import timezone
from django.db.models import Count

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView,CreateAPIView
from rest_framework import  status

from .serializers import (BroadcastSerializer, FacultySlotSerializer, PreviousSlotSerializer,
                            OngoingSlotSerializer,NextSlotSerializer,
                          InviteTokenVerifySerializer,FacultySignupSerializer,
                          BroadcastTargetSerializer
                          )
from base.permissions import IsAuthenticatedWithProfile
from base.models import Slot
from .models import FacultyProfile



class CreateAccountView(APIView):
    """
    Faculty signup using their Invite link.
    """
    permission_classes = [AllowAny]
    serializer_class = FacultySignupSerializer
    
    def get(self,request):
        """
        Verfies token and sends token context data.
        Used to populate the Faculty signup form in frontend.
        """
        token = InviteTokenVerifySerializer(data=request.query_params)
        token.is_valid(raise_exception=True)
        targetFaculty = token.save()

        userInfo = {'name': targetFaculty.name, 'invitedBy': targetFaculty.admin.name,
                     'email': targetFaculty.user.email}
        return Response({'status': 1, 'data': userInfo}, status=status.HTTP_200_OK)

    def post(self,request):
        """
        After verifying the token,
        Faculty account is created with given details.
        """
        signupDetails = FacultySignupSerializer(data=request.data)
        signupDetails.is_valid(raise_exception=True)

        token = {'token':signupDetails.validated_data.pop('token')}
        token = InviteTokenVerifySerializer(data=token)
        token.is_valid(raise_exception=True)
        targetFaculty = token.save()
        targetFaculty.claim_account(**signupDetails.validated_data)
        
        return Response({'status': 1, 'data': 'Faculty Account created successfully, login to continue.'},
                         status=status.HTTP_201_CREATED)
    

#TODO:Make a common class for both faculty and student view.
#TODO: check if refactoring is needed
class TimelineView(APIView):

    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = FacultyProfile
    required_account_active = True

    def get(self,request):
        #TODO:calc according to set timezone      
        currentDateTime = timezone.localtime()
        all_slots = Slot.objects.filter(faculty=request.profile,batch__active=True)\
                        .select_related('timing', 'batch')

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


        return Response({'status':1,'data':{'timelineData':timelineData,'weekdayData': jsonData}},status=status.HTTP_200_OK)


class BroadcastTargetView(ListAPIView):
    """
    Lists all the broadcast targets for the faculty to choose from i.e 
    all the available student groups that can receive the broadcast.
    """
    serializer_class = BroadcastTargetSerializer
    pagination_class = None
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = FacultyProfile
    required_account_active = True

    def get_queryset(self):
        return self.request.profile.assignedBatches()\
            .annotate(students_count=Count('students', distinct=True))

    def list(self,request,*args,**kwargs):
        response = super().list(request,*args,**kwargs)

        totalStudents = request.profile.assignedBatches()\
            .aggregate(total_students=Count('students')).pop('total_students')
        
        response.data.append({'label': f'Everyone , {totalStudents} students',
                              'value': 'EVERYONE'})
        
        response.data = reversed(response.data)

        return Response({'status':1,'data':response.data},status=status.HTTP_200_OK)


class BroadcastView(CreateAPIView):
    """
    Used to send broadcasts to students taught by the faculty.
    Can be sent to all students or students from a specific batch
    depending on the target field.
    """
    serializer_class = BroadcastSerializer
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = FacultyProfile
    required_account_active = True

    def perform_create(self, serializer):
        return serializer.save(sender=self.request.user)

