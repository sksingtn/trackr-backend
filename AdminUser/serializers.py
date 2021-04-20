from operator import itemgetter
from datetime import datetime,date

from rest_framework import serializers
from rest_framework.serializers import ValidationError
from django.db.models import Q
from django.utils import timezone

from base.models import CustomUser,FacultyProfile,Timing,Slot,Batch
from .utils import ApiErrors

class SignupSerializer(serializers.ModelSerializer):

    name = serializers.CharField(write_only=True)

    #Because default create would'nt hash the password.
    def create(self,validated_data):      
        return CustomUser.objects.create_user(**validated_data)
        

    class Meta:
        model = CustomUser
        fields = ['email','password','name']
        extra_kwargs = {'password':{'style':{'input_type': 'password'}}}


class FacultySerializer(serializers.ModelSerializer):

    class Meta:
        model = FacultyProfile
        fields = ['name','email','status','id','image']
        read_only_fields = ['id', 'status', 'image']

    email = serializers.EmailField(required=False)
    image = serializers.SerializerMethodField()

    def create(self,validated_data):
        """ Faculty Invite logic """
        email = validated_data.pop('email',False)
        if email:
            invited_user = CustomUser(email=email)
            invited_user.set_unusable_password()
            invited_user.save()
            validated_data['user'] = invited_user

            #Send An Invite Link here =>

        return FacultyProfile.objects.create(**validated_data)

    def get_image(self, instance):
        request = self.context.get('request')
        return request.build_absolute_uri(instance.image.url)

    def validate_email(self,data) :
        if CustomUser.objects.filter(email=data).exists():
            raise ValidationError('User with this email already exists!')
        return data

    def validate_name(self,data):
        admin_profile = self.context.get('profile')
        if admin_profile.invited_faculties.filter(name__iexact=data).exists():
            raise ValidationError('You already have a faculty with same name!')
        return data



class TimingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Timing
        fields = "__all__"


    def validate(self,validated_data):
        start,end = itemgetter('start_time','end_time')(validated_data)

        if start >= end:
            raise ValidationError(ApiErrors.START_TIME_GREATER)

        return validated_data

#Used for both read/write.
class SlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot

        fields = ['id','title', 'timing', 'batch', 'faculty',
                   'startTime', 'endTime','weekday','duration', 'created', 'facultyName']

        extra_kwargs = {'batch': {'write_only': True},
                        'faculty': {'write_only': True}}

        read_only_fields = ['id']

    timing = TimingSerializer(write_only=True)

    #Read Only Fields and methods
    startTime = serializers.SerializerMethodField(read_only=True)
    endTime = serializers.SerializerMethodField(read_only=True)
    duration = serializers.SerializerMethodField(read_only=True)
    created = serializers.SerializerMethodField(read_only=True)
    facultyName = serializers.CharField(source='faculty.name', read_only=True)
    weekday = serializers.CharField(source='timing.weekday',read_only=True)

    def get_startTime(self, instance):
        return instance.timing.start_time.strftime('%I:%M %p')

    def get_endTime(self, instance):
        return instance.timing.end_time.strftime('%I:%M %p')

    def get_duration(self, instance):
        #Cant subtract time from time so combined both with common date
        startTime = datetime.combine(date.today(), instance.timing.start_time)
        endTime = datetime.combine(date.today(), instance.timing.end_time)
        return f'{int((endTime-startTime).total_seconds()//60)} Mins'

    def get_created(self, instance):
        difference = (timezone.now()-instance.created)
        total_seconds = difference.total_seconds()

        if difference.days:
            value = f"{difference.days} day{'s' if difference.days > 1 else ''}"
        elif total_seconds//3600:
            hours = total_seconds//3600
            value = f"{int(hours)} hour{'s' if hours > 1 else ''}"
        elif total_seconds//60:
            minutes = total_seconds//60
            value = f"{int(minutes)} minute{'s' if minutes > 1 else ''}"
        else:
            value = f'{int(total_seconds)} seconds'

        return f'{value} ago'


    #Write Only methods.
    def create(self,validated_data):       
        validated_data['timing'],_ = Timing.objects.get_or_create(**validated_data.pop('timing'))
        
        return Slot.objects.create(**validated_data)

    def update(self,instance,validated_data):
        old_timing = instance.timing
        validated_data['timing'], _ = Timing.objects.get_or_create(**validated_data.pop('timing'))
        
        for key,value in validated_data.items():
            setattr(instance,key,value)        
        instance.save()

        #If timing is changed and the old timing has no attached slots. (Garbage Collection)
        if old_timing != instance.timing and not old_timing.slot_set.exists():
            old_timing.delete()

        return instance


    def validate(self,validated_data):       
        admin_profile = self.context.get('profile')       
        faculty = validated_data.get('faculty')
        batch = validated_data.get('batch')

        #During Slot update
        if self.instance and self.instance.batch != batch:
            raise ValidationError('Cant Move a slot to another batch!')
        

        #Making Sure that the requested Faculty/Batch is connected to the current Admin
        for index,item in enumerate([faculty.admin,batch.admin]):           
            if item != admin_profile:
                raise ValidationError(ApiErrors.NO_OWNERSHIP.format(resource = 'Batch' if index == 1 else 'Faculty',
                                                                                action = 'added' if index == 1 else 'invited'))


        self.start_time,self.end_time,self.weekday = itemgetter('start_time','end_time','weekday')(validated_data.get('timing'))

        all_slots = Slot.objects.filter(timing__weekday=self.weekday).filter(Q(faculty=faculty)|Q(batch=batch))
        overlapped_slot = all_slots.find_overlap(interval=(self.start_time,self.end_time),ignore=self.instance and self.instance.pk)


        if overlapped_slot is not None:
            #If overlap is with a slot in current batch.
            if overlapped_slot.batch == batch:
                raise ValidationError(ApiErrors.SLOT_OVERLAP.format(title=overlapped_slot.title,
                    start_time=overlapped_slot.get_start_time(),end_time=overlapped_slot.get_end_time()))
            #If overlap is with a slot in another batch which is taught by the requested faculty.
            else:
                raise ValidationError(ApiErrors.FACULTY_SLOT_OVERLAP.format(faculty=faculty.name,batch=overlapped_slot.batch.title,
                    start_time=overlapped_slot.get_start_time(),end_time=overlapped_slot.get_end_time()))
        
        return validated_data


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['id','title' ,'isActive', 'totalStudents',
                   'verifiedFaculties', 'totalClasses','created']

    isActive = serializers.BooleanField(source='active')
    totalStudents = serializers.SerializerMethodField()
    verifiedFaculties = serializers.SerializerMethodField()
    totalClasses = serializers.SerializerMethodField()


    def to_representation(self, obj):
        #Splitting into two fields, didnt make two serializer fields because of redundant calculation.
        res = super().to_representation(obj)
        verifiedFaculties, totalFaculties = res.pop('verifiedFaculties').split("/")
        res['verifiedFaculties'] = int(verifiedFaculties)
        res['totalFaculties'] = int(totalFaculties)
        return res 

    def get_totalStudents(self,instance):
        return instance.student_profiles.count()

    def get_verifiedFaculties(self,instance):
        #Could also use self.instance.connected_slots.distinct('faculty') but sqlite doesnt support it.
        total_faculties = set(FacultyProfile.objects.filter(slot__batch=instance))     
        verifiedFaculties = map(lambda profile: profile.status == "VERIFIED",total_faculties)                
        return f'{sum(verifiedFaculties)}/{len(total_faculties)}'

    def get_totalClasses(self,instance):
        return instance.connected_slots.count()


        
class SimpleBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['title', 'id']
        read_only_fields = ['id','active']

    def validate_title(self,title):
        admin_profile = self.context.get('profile')
        if admin_profile.batch_set.filter(title__iexact=title).exists():
            raise ValidationError('Batch with same title already exists!')

        return title



    

        




    

