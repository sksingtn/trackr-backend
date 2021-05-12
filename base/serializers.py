
from operator import itemgetter

from rest_framework import serializers
from base.models import Broadcast, Slot

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


class UserSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(style={'input_type': 'password'},write_only=True)


class BroadcastSerializer(serializers.ModelSerializer):

    class Meta:
        model = Broadcast
        fields = ['broadcast_type','text']

    broadcast_type = serializers.SerializerMethodField()

    def get_broadcast_type(self,instance):
        user,view = itemgetter('user','view')(self.context)
        if instance.sender == user:
            return view.SENT
        else:
            return view.RECEIVED