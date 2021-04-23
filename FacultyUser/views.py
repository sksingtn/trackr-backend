
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils import timezone


from .serializers import (FacultySlotSerializer,PreviousSlotSerializer,
                            OngoingSlotSerializer,NextSlotSerializer)
from .permissions import IsFaculty
from base.models import Slot



class TimelineView(APIView):

    permission_classes = [IsAuthenticated, IsFaculty]
    #Make a common class for both faculty and student view.
    def get(self,request):

        currentDateTime = timezone.localtime()
        all_slots = Slot.objects.filter(faculty=request.profile).select_related(
            'timing', 'batch')
       
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
