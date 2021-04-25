from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework import status
from django.utils import timezone


from .serializers import (StudentSlotSerializer, PreviousSlotSerializer,
                          OngoingSlotSerializer, NextSlotSerializer)
from .permissions import IsStudent
from base.models import Slot


class TimelineView(APIView):

    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):

        batch = request.profile.batch

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
