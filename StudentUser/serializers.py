
from AdminUser.serializers import SlotSerializer
from rest_framework import serializers
from base.models import Slot
from base.serializers import (
    BasePreviousSlotSerializer, BaseOngoingSlotSerializer, BaseNextSlotSerializer)


class StudentSlotSerializer(SlotSerializer):
    pass


class OngoingSlotSerializer(BaseOngoingSlotSerializer):

    facultyName = serializers.CharField(source='faculty.name', read_only=True)

    class Meta(BaseOngoingSlotSerializer.Meta):
        model = Slot
        fields = BaseOngoingSlotSerializer.Meta.fields + ['facultyName']


class PreviousSlotSerializer(BasePreviousSlotSerializer):

    facultyName = serializers.CharField(source='faculty.name', read_only=True)

    class Meta(BasePreviousSlotSerializer.Meta):
        model = Slot
        fields = BasePreviousSlotSerializer.Meta.fields + ['facultyName'] 



class NextSlotSerializer(BaseNextSlotSerializer):

    facultyName = serializers.CharField(source='faculty.name', read_only=True)

    class Meta(BaseNextSlotSerializer.Meta):
        model = Slot
        fields = BaseNextSlotSerializer.Meta.fields + ['facultyName']




