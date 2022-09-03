
from uuid import UUID
from operator import itemgetter
import uuid

from django.core import signing
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import FacultyProfile
from base.models import Batch, Slot,Broadcast
from trackr.settings import FACULTY_INVITE_MAX_AGE
from base.serializers import BaseOngoingSlotSerializer,BaseNextOrPreviousSlotSerializer                                
from StudentUser.models import StudentProfile
from base.utils import PasswordMinLengthValidator




#Added Batch field to all the faculty serializer classes
class OngoingSlotSerializer(BaseOngoingSlotSerializer):

    class Meta(BaseOngoingSlotSerializer.Meta):
        model = Slot
        fields = BaseOngoingSlotSerializer.Meta.fields + ['batch']

    batch = serializers.CharField(source='batch.title')
        

class NextOrPreviousSlotSerializer(BaseNextOrPreviousSlotSerializer):

    class Meta(BaseNextOrPreviousSlotSerializer.Meta):
        model = Slot
        fields = BaseNextOrPreviousSlotSerializer.Meta.fields + ['batch']

    batch = serializers.CharField(source='batch.title')


class InviteTokenVerifySerializer(serializers.Serializer):
    """
    Validates the Faculty Invite token and returns
    the FacultyProfile object pertaining to the token.
    """
    token = serializers.CharField(write_only=True)

    def create(self,validated_data):
        token_context = validated_data['token']
        email, admin = itemgetter('email', 'invitedBy')(token_context)
        try:
            target_user = FacultyProfile.objects.select_related('user','admin')\
                            .get(admin__uuid=admin,user__email=email)
            assert target_user.status != target_user.VERIFIED,'You have already added your account'

        except (FacultyProfile.DoesNotExist,FacultyProfile.MultipleObjectsReturned):
            raise ValidationError('Link is not valid anymore!')

        except AssertionError as e:
            raise ValidationError(str(e))

        return target_user
         
    def validate_token(self,data):
        try:
            token_context = signing.loads(data,max_age=FACULTY_INVITE_MAX_AGE)
            #Check presence of following keys.
            itemgetter('email', 'invitedBy')(token_context)
            #raises ValueError if not a UUID.
            token_context['invitedBy'] = uuid.UUID(token_context['invitedBy'])
        except signing.SignatureExpired:
            raise ValidationError('Link has expired')
        except (signing.BadSignature,KeyError,ValueError) as e:
            raise ValidationError('Link is Invalid!') 
        except Exception:
            raise ValidationError('Something went wrong!')

        return token_context


class FacultySignupSerializer(serializers.Serializer):
    token = serializers.CharField()
    receive_email_notification = serializers.BooleanField()
    password = serializers.CharField(style={'input_type': 'password'},
                    validators=[PasswordMinLengthValidator(8)])


class BroadcastTargetSerializer(serializers.ModelSerializer):
    """
    List all the available broadcast target for a faculty.
    """
    class Meta:
        model = Batch
        fields = ['label', 'value']

    label = serializers.SerializerMethodField()
    value = serializers.CharField(source='uuid')

    def get_label(self,instance):
        return f'{instance.title} , {instance.students_count} students'


class BroadcastSerializer(serializers.ModelSerializer):
    """
    Creates a Broadcast instance where faculties are senders
    and receivers are specified by the target field.
    """
    class Meta:
        model = Broadcast
        fields = ['text','target']

    target = serializers.CharField()
    text = serializers.CharField(style={'base_template': 'textarea.html'})

    def create(self,validated_data):
        text,sender,receivers = itemgetter('text','sender','receivers')(validated_data)
        broadcast = Broadcast.objects.create(sender=sender,text=text)
        broadcast.receivers.add(*receivers)
        return broadcast

    def validate_text(self,text):
        if len(text) > 500:
            raise ValidationError('Text cant exceed 500 characters!')
        return text

    def validate(self,validated_data):
        target = validated_data.get('target')
        facultyProfile = self.context['request'].profile

        allBatches = list(facultyProfile.assignedBatches().values_list('uuid',flat=True))
        
        if target == 'EVERYONE':
            targetStudents = StudentProfile.objects.filter(batch__uuid__in=allBatches)
       
        else:
            try:
                target = UUID(target)
            except ValueError:
                raise ValidationError('Invalid target!')

            if target not in allBatches:
                raise ValidationError("You are not allowed to send broadcasts in this batch!")

            targetStudents = StudentProfile.objects.filter(batch__uuid=target)

        if targetStudents.count() == 0:
            raise ValidationError("No students are present to receive the broadcast!")

        validated_data['receivers'] = [students.user for students in targetStudents]

        return validated_data

    def to_representation(self, instance):
        sent_to = instance.receivers.count()
        return {'status': 1, 'data': f'Broadcast sent to {sent_to} people.'}

