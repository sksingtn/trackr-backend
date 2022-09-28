from multiprocessing import context
from operator import itemgetter
from itertools import groupby
from datetime import timedelta,datetime

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from trackr.settings import WEEKDAYS
from .utils import get_time_difference
from . import response


class SlotQuerySet(models.QuerySet):

    def detect_overlap(self, startTime,endTime,batch):
        """
        Tries to find a slot which overlaps with the given requested start & end time.
        Adjacent Slots are alllowed i.e 07:00-08:00,08:00-09:00

        If a overlapping slot is found then 2 errors are possible : 
        1. The overlapping slot is from the same batch where a new slot was requested.
        2. The overlapping slot is from a different batch which means the requested
            faculty already has assigned slot in a different batch at the requested time.
        """

        leftOverlap = Q(start_time__gte=startTime,
                        start_time__lt=endTime)

        rightOverlap = Q(end_time__gt=startTime,
                        end_time__lte=endTime)

        edgeCase = Q(start_time__lte=startTime,
                     end_time__gte=endTime)

        overlappedSlot = self.filter(leftOverlap | rightOverlap | edgeCase).first()

        if overlappedSlot is not None:
            overlappedStartTime = overlappedSlot.get_start_time()
            overlappedEndTime = overlappedSlot.get_end_time()

            if overlappedSlot.batch == batch:
                raise DjangoValidationError(response\
                    .overlappedSlotResponse(overlappedSlot.title,overlappedStartTime,overlappedEndTime))
            else:
                raise DjangoValidationError(response\
                    .overlappedFacultyResponse(overlappedSlot.faculty.name,overlappedSlot.batch.title
                                               ,overlappedStartTime,overlappedEndTime))



    def serialize_and_group_by_weekday(self,*,serializer,context=None):
        all_slots = serializer(self,context=context, many=True).data

        groupedData = {}
        getWeekday = itemgetter('weekday')
        #Data always needs to be sorted when passed to groupby
        for weekday,slots in groupby(sorted(all_slots,key=getWeekday),key=getWeekday):
            
            slots = list(slots)
            for item in slots:
                item.pop('weekday')
            groupedData[weekday] = slots
      
        #Initialize weekdays with no slots with an empty list.
        remainingWeekdays = set(WEEKDAYS) - groupedData.keys()
        #These will always remain [], so initializing with [] is not a problem.
        remainingWeekdays = {}.fromkeys(remainingWeekdays,[])
        groupedData.update(remainingWeekdays)

        #Sort by weekday and return as list of dicts.
        response = []
        for key,value in sorted(groupedData.items(),key=lambda x : WEEKDAYS.index(x[0])):
            response.append({'weekday':key,'data':value})
            
        return response

    def find_previous_ongoing_next_slot(self,tz,pSerializer,oSerializer,nSerializer):
        """
        1. If the slot is ongoing relative to currentDateTime then 
           elapsed seconds is returned.
        2. If the slot has already happened this week relative to currentDateTime then
           'ended since' seconds are returned.
        3. If the slot is about to happen this week relative to currentDateTime then
            'starts in' seconds are returned.
        """
        currentDateTime = timezone.localtime().astimezone(tz)
        currentWeekday = currentDateTime.weekday()
        currentDate = currentDateTime.date()
        currentTime = currentDateTime.time()
        timelineInfo = {"previousSlot":None
                        ,"ongoingSlot":None
                        ,"nextSlot":None}


        previousSlot = self.filter(Q(weekday=currentWeekday, end_time__lte=currentTime) |
                                        Q(weekday__lt=currentWeekday)).order_by('weekday', 'start_time').last()
        if previousSlot is not None:
            dayOffset = previousSlot.weekday - currentDateTime.weekday()
            compareDate = currentDate + timedelta(days=dayOffset)
            compareDateTime = datetime.combine(compareDate,previousSlot.end_time,)
            passedSinceSeconds = (currentDateTime - tz.localize(compareDateTime)).total_seconds()
            timelineInfo["previousSlot"] = {**pSerializer(previousSlot
                                            ,context={"currentDateTime":currentDateTime}).data,
                                            "passedSinceSeconds":int(passedSinceSeconds)}

        ongoingSlot = self.filter(weekday=currentWeekday,
                                    start_time__lte=currentTime, end_time__gt=currentTime).first()
        if ongoingSlot is not None:
            elapsedSeconds = get_time_difference(currentTime,ongoingSlot.start_time)
            timelineInfo["ongoingSlot"] = {**oSerializer(ongoingSlot).data,
                                            "elapsedSeconds":int(elapsedSeconds)}

        nextSlot = self.filter(Q(weekday=currentWeekday, start_time__gt=currentTime) |
                                    Q(weekday__gt=currentWeekday)).order_by('weekday', 'start_time').first()
        if nextSlot is not None:
            dayOffset = nextSlot.weekday - currentDateTime.weekday()
            compareDate = currentDate + timedelta(days=dayOffset)
            compareDateTime = datetime.combine(compareDate,nextSlot.start_time)
            startsInSeconds = (tz.localize(compareDateTime) - currentDateTime).total_seconds()
            timelineInfo["nextSlot"] = {**nSerializer(nextSlot
                                            ,context={"currentDateTime":currentDateTime}).data,
                                            "startsInSeconds":int(startsInSeconds)}

        return timelineInfo


class SlotManager(models.Manager):

    def get_queryset(self):
        return SlotQuerySet(model=self.model, using=self._db)

    def possible_overlap_queryset(self,weekday,faculty,batch):
        """
        Returns the slots that could overlap if a new slot
        with the given weekday,faculty & batch is created.
        """
        return self.get_queryset().filter(weekday=weekday)\
                .filter(Q(faculty=faculty)|Q(batch=batch))



#TODO:Test for obsoleteness
class BatchQueryset(models.QuerySet):
    pass

class BatchManager(models.Manager):
    def get_queryset(self):
        return BatchQueryset(model=self.model, using=self._db)

