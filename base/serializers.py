
from rest_framework import serializers
from base.models import Slot

#A base class is also needed here to enfore DRY.

class BaseOngoingSlotSerializer(serializers.ModelSerializer):

    startTime = serializers.CharField(source='timing.get_start_time')
    endTime = serializers.CharField(source='timing.get_end_time')
    totalSeconds = serializers.IntegerField(source='timing.get_duration_in_seconds')
    elapsedSeconds = serializers.SerializerMethodField()

    def get_elapsedSeconds(self, instance):
        return instance.timing.get_elapsed_seconds(currentDateTime=self.context['currentDateTime'])

    class Meta:
        model = Slot
        fields = ['title', 'startTime',
                  'endTime', 'totalSeconds', 'elapsedSeconds']



class BasePreviousSlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = ['title', 'endedSince',
                  'startTime', 'endTime', 'weekday']

    endedSince = serializers.SerializerMethodField()
    startTime = serializers.CharField(source='timing.get_start_time')
    endTime = serializers.CharField(source='timing.get_end_time')
    weekday = serializers.SerializerMethodField()

    def get_weekday(self, instance):
        currentWeekDay = self.context['currentDateTime'].weekday()

        if instance.timing.weekday == currentWeekDay:
            return 'Today'
        else:
            return instance.timing.get_weekday_string()

    def get_endedSince(self, instance):
        return instance.timing.get_elapsed(currentDateTime=self.context['currentDateTime'])


class BaseNextSlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = ['title', 'startsIn',
                  'startTime', 'endTime', 'weekday']

    startsIn = serializers.SerializerMethodField()
    startTime = serializers.CharField(source='timing.get_start_time')
    endTime = serializers.CharField(source='timing.get_end_time')
    weekday = serializers.SerializerMethodField()

    def get_weekday(self, instance):
        currentWeekDay = self.context['currentDateTime'].weekday()

        if instance.timing.weekday == currentWeekDay:
            return 'Today'
        else:
            return instance.timing.get_weekday_string()

    def get_startsIn(self, instance):
        return instance.timing.get_elapsed(currentDateTime=self.context['currentDateTime'])
