
from uuid import UUID

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from AdminUser.serializers import SlotSerializer
from base.models import Slot,Batch
from .models import StudentProfile
from base.serializers import (
    BasePreviousSlotSerializer, BaseOngoingSlotSerializer, BaseNextSlotSerializer)
from base.utils import unique_email_validator,PasswordMinLengthValidator


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



class InviteLinkVerifySerializer(serializers.Serializer):
    """
    Validates the Student Invite token and returns 
    the batch object pertaining to the token.
    """
    token = serializers.CharField() 
    
    def create(self,validated_data):
        token = validated_data['token']

        try:
            batch = Batch.objects.select_related('admin').get(uuid=token)
            assert batch.onboard_students , 'Student onboarding for this batch has been stopped by the Admin!'
            assert batch.total_students() < batch.max_students,'Batched has reached max students!'
        except (Batch.DoesNotExist,Batch.MultipleObjectsReturned):
            raise ValidationError('Link is Invalid!')
        except AssertionError as e:
            raise ValidationError(str(e))
        
        return batch

    def validate_token(self,token):
        try:
            token = UUID(token)
        except (ValueError):
            raise ValidationError('Link is Invalid!')
        return token


class StudentSignupSerializer(serializers.Serializer):

    name = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'},
                validators=[PasswordMinLengthValidator(8)])
    email = serializers.EmailField(validators=[unique_email_validator])
    receive_email_notification = serializers.BooleanField()
    token = serializers.CharField()

    def create(self,validated_data):
        return StudentProfile.create_profile(**validated_data)









    




