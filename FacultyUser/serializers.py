
from rest_framework import serializers

from base.models import Slot
from AdminUser.serializers import SlotSerializer
from base.serializers import (BasePreviousSlotSerializer,BaseOngoingSlotSerializer,BaseNextSlotSerializer)


class FacultySlotSerializer(SlotSerializer):
    #Extending to add batch and remove facultyName
    batch = serializers.CharField(source='batch.title')

    class Meta(SlotSerializer.Meta):
        fields = ['id', 'title', 'startTime', 'endTime','weekday', 'duration', 'created', 'batch']



#Added Batch field to all the faculty serializer classes

class OngoingSlotSerializer(BaseOngoingSlotSerializer):

    batch = serializers.CharField(source='batch.title')

    class Meta(BaseOngoingSlotSerializer.Meta):
        model = Slot
        fields = BaseOngoingSlotSerializer.Meta.fields + ['batch']

        

class PreviousSlotSerializer(BasePreviousSlotSerializer):

    class Meta(BasePreviousSlotSerializer.Meta):
        model = Slot
        fields = BasePreviousSlotSerializer.Meta.fields + ['batch']

    batch = serializers.CharField(source='batch.title')


class NextSlotSerializer(BaseNextSlotSerializer):

    class Meta(BaseNextSlotSerializer.Meta):
        model = Slot
        fields = BaseNextSlotSerializer.Meta.fields + ['batch']

    batch = serializers.CharField(source='batch.title')

