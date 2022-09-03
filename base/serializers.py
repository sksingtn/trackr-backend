
from rest_framework import serializers

from base.models import Activity, CustomUser, Slot
from base.utils import get_elapsed_string

"""
Slot Display Serializers for Admin,Faculty & students.
"""
class BaseSlotDisplaySerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = ['id','title', 'startTime', 'endTime',
                'weekday','duration', 'lastModified']

    id = serializers.CharField(source='uuid')
    startTime = serializers.CharField(source='get_start_time')
    endTime = serializers.CharField(source='get_end_time')
    weekday = serializers.CharField(source='get_weekday_string')
    duration = serializers.CharField(source='get_duration')
    lastModified = serializers.CharField(source='get_last_modified')


class FacultySlotDisplaySerializer(BaseSlotDisplaySerializer):
    """
    Inherited BaseSlotDisplaySerializer and added batch name
    to each slot which is needed in Faculty perspective.
    """
    class Meta(BaseSlotDisplaySerializer.Meta):
        fields = BaseSlotDisplaySerializer.Meta.fields + ['batch']

    batch = serializers.CharField(source='batch.title')


class SlotDisplayWithFacultySerializer(BaseSlotDisplaySerializer):
    """
    Inherited BaseSlotDisplaySerializer and added faculty profile details
    to each slot which is needed in Student & Admin perspective.
    """
    class Meta(BaseSlotDisplaySerializer.Meta):
        fields = BaseSlotDisplaySerializer.Meta.fields + ['faculty']

    faculty = serializers.SerializerMethodField()

    def get_faculty(self,instance):
        request = self.context.get('request')
        faculty = instance.faculty
        return {'id':faculty.uuid,'name':faculty.name
                ,'image':faculty.get_profile_image(request)}

class StudentSlotDisplaySerializer(SlotDisplayWithFacultySerializer):
    pass

class AdminSlotDisplaySerializer(SlotDisplayWithFacultySerializer):
    pass


"""
Serializers for Previous,Ongoing,Upcoming Slots.
"""
class BaseOngoingSlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = ['title', 'startTime','endTime', 'totalSeconds']

    startTime = serializers.CharField(source='get_start_time')
    endTime = serializers.CharField(source='get_end_time')
    totalSeconds = serializers.IntegerField(source='get_duration_in_seconds')


class BaseNextOrPreviousSlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = ['title','startTime','endTime', 'weekday']

    startTime = serializers.CharField(source='get_start_time')
    endTime = serializers.CharField(source='get_end_time')
    weekday = serializers.SerializerMethodField()

    def get_weekday(self, instance):
        currentWeekDay = self.context['currentDateTime'].weekday()

        if instance.weekday == currentWeekDay:
            return 'Today'
        else:
            return instance.get_weekday_string()


class UserSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(style={'input_type': 'password'},write_only=True)


class ActivitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Activity
        fields = ['text','read','created']

    created = serializers.SerializerMethodField()

    def get_created(self,instance):
        return get_elapsed_string(instance.created)


class UserImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['profile_image']

    #Required
    profile_image = serializers.ImageField(allow_null=False, max_length=100, required=True)
