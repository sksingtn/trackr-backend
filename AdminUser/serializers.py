from operator import itemgetter

from rest_framework import serializers
from rest_framework.serializers import ValidationError
from django.db.models import Q  

from base.models import Timing, Slot, Batch, CustomUser
from FacultyUser.models import FacultyProfile 
from StudentUser.models import StudentProfile
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
        email = validated_data.pop('email',False)
        return FacultyProfile.create_profile(**validated_data,email=email)

    def get_image(self, instance):
        request = self.context.get('request')
        return request.build_absolute_uri(instance.image.url)

    #Need to reuse
    def validate_email(self,data) :
        if CustomUser.objects.filter(email=data).exists():
            raise ValidationError('User with this email already exists!')
        return data

    def validate_name(self,data):
        admin_profile = self.context.get('profile')
        if admin_profile.invited_faculties.filter(name__iexact=data).exists():
            raise ValidationError('You already have a faculty with same name!')
        return data


class FacultyEmailSerializer(FacultySerializer):
    class Meta(FacultySerializer.Meta):
        fields = ['email']
        #read_only_fields = ['id', 'status', 'image']


class FacultyDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = FacultyProfile
        fields = ['id','name','email', 'status', 'image','classes']

    classes = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email',default=None)

    def get_classes(self,instance):
        totalBatches = Batch.objects.filter(connected_slots__faculty=instance).distinct().count()
        totalClasses = Slot.objects.filter(faculty=instance).count()

        if not totalClasses:
            msg = 'No classes'
        else:
            totalClasses = f'{totalClasses} class{"es" if totalClasses>1 else ""}'
            totalBatches = f'{totalBatches} batch{"es" if totalBatches>1 else ""}'
            msg = f'{totalClasses} in {totalBatches}'
        return msg


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
#Make it a base serializer for student and admin maybe?
class SlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot

        fields = ['id','title', 'timing', 'batch', 'faculty',
                   'startTime', 'endTime','weekday','duration', 'created', 'facultyName']

        extra_kwargs = {'batch': {'write_only': True},
                        'faculty': {'write_only': True}}

        #Move this into extra_kwargs
        read_only_fields = ['id']

    timing = TimingSerializer(write_only=True)

    #Read Only Fields
    startTime = serializers.CharField(read_only=True,source='timing.get_start_time')
    endTime = serializers.CharField(read_only=True,source='timing.get_end_time')
    weekday = serializers.CharField(read_only=True,source='timing.get_weekday_string')
    duration = serializers.CharField(read_only=True,source='timing.get_duration')
    created = serializers.CharField(read_only=True, source='get_last_activity')
    facultyName = serializers.CharField(source='faculty.name', read_only=True)


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


        #Move this logic to Slot create/update
        self.start_time,self.end_time,self.weekday = itemgetter('start_time','end_time','weekday')(validated_data.get('timing'))

        all_slots = Slot.objects.filter(timing__weekday=self.weekday).filter(Q(faculty=faculty)|Q(batch=batch))
        if self.instance:
            all_slots = all_slots.exclude(pk=self.instance.pk)

        overlapped_slot = all_slots.detect_overlap(interval=(self.start_time,self.end_time))


        if overlapped_slot is not None:
            start_time = overlapped_slot.timing.get_start_time()
            end_time = overlapped_slot.timing.get_end_time()

            #If overlap is with a slot in current batch.
            if overlapped_slot.batch == batch:
                raise ValidationError(ApiErrors.SLOT_OVERLAP.format(title=overlapped_slot.title,
                                     start_time=start_time,end_time=end_time))
            #If overlap is with a slot in another batch which is taught by the requested faculty.
            else:
                raise ValidationError(ApiErrors.FACULTY_SLOT_OVERLAP.format(faculty=faculty.name,batch=overlapped_slot.batch.title,
                                      start_time=start_time,end_time=end_time))
        
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
        #Needs Refactoring
        #Could also use self.instance.connected_slots.distinct('faculty') but sqlite doesnt support it.
        total_faculties = set(FacultyProfile.objects.filter(slot__batch=instance))     
        verifiedFaculties = map(lambda profile: profile.status == "VERIFIED",total_faculties)                
        return f'{sum(verifiedFaculties)}/{len(total_faculties)}'

    def get_totalClasses(self,instance):
        return instance.connected_slots.count()


class BatchDetailSerializer(BatchSerializer):

    class Meta(BatchSerializer.Meta):
        fields = BatchSerializer.Meta.fields + \
            ['onboardStudents', 'maxStudents', 'inviteLink']

    inviteLink = serializers.SerializerMethodField(read_only=True)
    onboardStudents = serializers.BooleanField(source='onboard_students')
    maxStudents = serializers.IntegerField(source='max_students')

    def get_inviteLink(self,instance):
        return instance.uuid


class BatchEditSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Batch
        fields = ['title','max_students','onboard_students']

        extra_kwargs = {'title':{'required':False}}

    def validate_title(self,data):
        admin = self.context.get('profile')

        if admin.batch_set.filter(title__iexact=data).exists():
            raise ValidationError('Batch with the requested title already exists!')
        return data

    def validate_max_students(self,data):
        if data <= 0:
            raise ValidationError('Max Students has to be greater than 0!')

        if data < self.instance.student_profiles.count():
            raise ValidationError('Max students can\'t be lower than current student count!')
        return data

    
    
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


class StudentIdSerializer(serializers.Serializer): 
    students = serializers.ListField(child=serializers.IntegerField(),allow_empty=True)


class StudentDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentProfile
        fields = ['id','name','image','joined','email']

    image = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email')

    def get_image(self, instance):
        request = self.context.get('request')
        return request.build_absolute_uri(instance.image.url)

    def get_joined(self,instance):
        return instance.joined.strftime('%d %b %Y')



    

        




    

