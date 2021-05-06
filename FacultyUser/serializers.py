
from operator import itemgetter

from django.core import signing
from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import FacultyProfile
from base.models import Slot
from AdminUser.serializers import SlotSerializer
from AdminUser.utils import FACULTY_INVITE_MAX_AGE
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


class InviteTokenVerifySerializer(serializers.Serializer):
  
    token = serializers.CharField(write_only=True)

    def create(self,validated_data):
        token_context = validated_data['token']
        #Convert into UUID instance first.
        email,admin = token_context['email'],token_context['invited_by']
        try:
            target_user = FacultyProfile.objects.select_related('user','admin').get(admin__uuid=admin,user__email=email)
            assert target_user.status != target_user.VERIFIED,'You have already added your account'

        except (FacultyProfile.DoesNotExist,FacultyProfile.MultipleObjectsReturned):
            raise ValidationError('Link is not valid anymore!')

        except AssertionError as e:
            raise ValidationError(str(e))

        #Supplied optionally by view in save()
        password = validated_data.get('password')
        if password is not None:
            #Update the joined field
            target_user.user.set_password(password)
            target_user.user.save()

        return target_user
         
    def validate_token(self,data):
        try:
            context = signing.loads(data,max_age=FACULTY_INVITE_MAX_AGE)
            itemgetter('email', 'invited_by')(context)
        except (signing.BadSignature,KeyError) as e:
            raise ValidationError(f'Link is Invalid!') 
        except signing.SignatureExpired:
            raise ValidationError('Link has expired')
        except Exception:
            raise ValidationError('Something went wrong!')

        return context


class FacultyPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(style={'input_type': 'password'},write_only=True)

    #need reuse
    def validate_password(self,data):

        try:
            MinimumLengthValidator(min_length=8).validate(data)
        except DjangoValidationError:
            raise ValidationError('Password must be 8 characters long!')

        return data

