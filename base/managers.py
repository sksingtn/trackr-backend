from collections import defaultdict

from django.db import models
from django.db.models import Q

from .utils import WEEKDAYS


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

    def serialize_and_group_by_weekday(self,serializer):
        all_slots = serializer(self, many=True)
        weekday_dict = defaultdict(list)
        for item in all_slots.data:
            try:
                weekday_dict[item.pop('weekday')].append(item)
            except KeyError:
                raise Exception('Serializer must have a weekday field!')

        #Fill the empty weekdays with empty list.
        remaining = ({}.fromkeys(set(WEEKDAYS).difference(weekday_dict.keys()), []))
        weekday_dict.update(remaining)

        #Sort them by weekday
        return dict(sorted(weekday_dict.items(),key=lambda x: WEEKDAYS.index(x[0])))

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
