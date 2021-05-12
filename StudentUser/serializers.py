
from uuid import UUID

from rest_framework.exceptions import ValidationError
from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.exceptions import ValidationError as DjangoValidationError


from AdminUser.serializers import SlotSerializer
from rest_framework import serializers
from base.models import Slot,Batch,CustomUser
from .models import StudentProfile
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



class InviteLinkVerifySerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True) 
    #Maybe move the create to view?
    def create(self,validated_data):
        token = validated_data['token']

        try:
            batch = Batch.objects.select_related('admin').get(uuid=token)
            assert batch.onboard_students , 'Student onboarding for this batch has been stopped by the Admin!'
            assert batch.student_profiles.count() < batch.max_students,'Batched has reached max students!'
        except (Batch.DoesNotExist,Batch.MultipleObjectsReturned):
            raise ValidationError('Link is Invalid!')
        except AssertionError as e:
            raise ValidationError(str(e))
        
        return batch

    def validate_token(self,data):
        try:
            data = UUID(data)
            assert data.version == 4
        except (ValueError,AssertionError):
            raise ValidationError('Link is Invalid!')
        return data


class CreateStudentSerializer(serializers.Serializer):

    name = serializers.CharField()
    password = serializers.CharField(validators=[MinimumLengthValidator])
    email = serializers.EmailField()

    def create(self,validated_data):
        from base.models import CustomUser
        user = CustomUser(email=validated_data['email'],user_type=CustomUser.STUDENT)
        user.set_password(validated_data['password'])
        user.full_clean()
        user.save()

        return StudentProfile.objects.create(user=user,name=validated_data['name'],
                batch=validated_data['batch'],joined=validated_data['joined'])

    def validate_email(self, data):
        if CustomUser.objects.filter(email=data).exists():
            raise ValidationError('User with this email already exists!')
        return data

    def validate_password(self, data):

        try:
            MinimumLengthValidator(min_length=8).validate(data)
        except DjangoValidationError:
            raise ValidationError('Password must be 8 characters long!')

        return data




    




