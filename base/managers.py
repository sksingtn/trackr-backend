from operator import itemgetter
from itertools import groupby

from django.db import models
from django.db.models import Q

from trackr.settings import WEEKDAYS


class SlotQuerySet(models.QuerySet):

    def detect_overlap(self, interval: tuple):
        """
        Tries to find a slot which overlaps with the given start_time-end_time interval.
        If found returns the first slot.
        """
        start_time, end_time = interval
        edgeCase = Q(timing__start_time__lte=start_time,
                     timing__end_time__gte=end_time)

        return self.filter(Q(timing__start_time__range=interval) |
                           Q(timing__end_time__range=interval) | edgeCase).first()

    def serialize_and_group_by_weekday(self,*,serializer):
        all_slots = serializer(self, many=True).data

        groupedData = {}
        for weekday,slots in groupby(all_slots,key=itemgetter('weekday')):
            
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

    def find_previous_ongoing_next_slot(self,currentDateTime):
        currentWeekday = currentDateTime.weekday()
        currentTime = currentDateTime.time()

        ongoingSlot = self.filter(timing__weekday=currentWeekday,
                                    timing__start_time__lte=currentTime, timing__end_time__gte=currentTime).first()

        previousSlot = self.filter(Q(timing__weekday=currentWeekday, timing__end_time__lt=currentTime) |
                                        Q(timing__weekday__lt=currentWeekday)).order_by('timing__weekday', 'timing__start_time').last()

        nextSlot = self.filter(Q(timing__weekday=currentWeekday, timing__start_time__gt=currentTime) |
                                    Q(timing__weekday__gt=currentWeekday)).order_by('timing__weekday', 'timing__start_time').first()

        return previousSlot,ongoingSlot,nextSlot


class SlotManager(models.Manager):

    def get_queryset(self):
        return SlotQuerySet(model=self.model, using=self._db)



#TODO:Test for obsoleteness

class BatchQueryset(models.QuerySet):
    pass

class BatchManager(models.Manager):
    def get_queryset(self):
        return BatchQueryset(model=self.model, using=self._db)

