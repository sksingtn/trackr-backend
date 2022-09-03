
from urllib import request
from uuid import UUID
from operator import itemgetter

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers
from rest_framework.serializers import ValidationError

from base.models import Slot, Batch,Broadcast
from FacultyUser.models import FacultyProfile  
from StudentUser.models import StudentProfile
from .models import AdminProfile
from base.utils import PasswordMinLengthValidator, unique_email_validator,get_image
from base.serializers import AdminSlotDisplaySerializer
from base import response


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[unique_email_validator])


class AdminSignupSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdminProfile
        fields = ['name','email','password','timezone']
        
    name = serializers.CharField()
    email = serializers.EmailField(validators=[unique_email_validator])
    password = serializers.CharField(style={'input_type': 'password'},
                validators=[PasswordMinLengthValidator(8)])
    
    def create(self,validated_data):      
        return AdminProfile.create_profile(**validated_data)

    def to_representation(self, instance):
        return {'status':1,'data':'Admin Account created successfully, login to continue.'}
    
        
""" Faculty Serializers from Admin perspective """

class FacultySerializer(serializers.ModelSerializer):
    """
    Used for both creation & listing of faculty accounts.
    """
    class Meta:
        model = FacultyProfile
        fields = ['name','email','status','id','image']
        read_only_fields = ['status', 'image']

    id = serializers.CharField(source='uuid',read_only=True)
    email = serializers.EmailField(required=False,write_only=True,validators=[unique_email_validator])
    image = serializers.SerializerMethodField()

    def get_image(self, instance):      
        request = self.context.get('request')
        return instance.get_profile_image(request,thumbnail=True)

    def create(self,validated_data):
        email = validated_data.pop('email',None)
        return FacultyProfile.create_profile(**validated_data,email=email)

    def validate_name(self,name):
        adminProfile = self.context.get('request').profile
        if adminProfile.connected_faculties.filter(name__iexact=name).exists():
            raise ValidationError('You already have a faculty with same name!')
        return name

    def to_representation(self, instance):
        
        if self.context.get('request').method == 'POST':           
            if instance.user is not None:
                msg = 'User Invited Successfully!'
            else:
                msg = 'User Added SuccessFully!'
            
            return {'status':1,'data':msg}

        return super().to_representation(instance)


class FacultySlotSerializer(serializers.ModelSerializer):
    """
    Used Internally by FacultyDetailSerializer
    """
    class Meta:
        model = Slot
        fields = ['title', 'batch', 'weekday', 'startTime', 'endTime']

    batch = serializers.CharField(source='batch.title')
    weekday = serializers.CharField(source='get_weekday_string')
    startTime = serializers.CharField(source='get_start_time')
    endTime = serializers.CharField(source='get_end_time')


class FacultyBatchSerializer(serializers.ModelSerializer):
    """
    Used Internally by FacultyDetailSerializer
    """
    class Meta:
        model=Batch
        fields = ['title', 'totalStudents']

    totalStudents = serializers.IntegerField(source='total_students')


class FacultyDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = FacultyProfile
        fields = ['id', 'name', 'email', 'status',
                  'image', 'assignedClasses', 'assignedBatches','joined']
    
    id = serializers.CharField(source='uuid', read_only=True)
    email = serializers.CharField(source='user.email',default=None)
    image = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    assignedClasses = serializers.SerializerMethodField()
    assignedBatches = serializers.SerializerMethodField()

    def get_image(self, instance):      
        request = self.context.get('request')
        return instance.get_profile_image(request,thumbnail=True)

    def get_joined(self,instance):
        return instance.joined and instance.joined.strftime('%d %b %Y')

    def get_assignedClasses(self,instance):
        allTaughtSlots = instance.teaches_in.order_by('weekday','start_time')   
        return FacultySlotSerializer(allTaughtSlots,many=True).data

    def get_assignedBatches(self,instance):
        allTaughtBatches = instance.assignedBatches()
        return FacultyBatchSerializer(allTaughtBatches,many=True).data    


""" Slot Serializers """

class SlotCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot

        fields = ['title', 'batch', 'faculty',
                   'start_time', 'end_time','weekday']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'context' in kwargs:
            if 'request' in kwargs['context'] and \
                    kwargs['context']['request'].method == 'PUT':
                self.fields.pop('batch')
                
    batch = serializers.SlugRelatedField(queryset=Batch.objects.all(),slug_field='uuid')
    faculty = serializers.SlugRelatedField(queryset=FacultyProfile.objects.all(),slug_field='uuid')

    def create(self,validated_data):    
        try:
            slot = Slot.create_slot(**validated_data)          
        except DjangoValidationError as err:        
            raise ValidationError(err.message)
        return slot

    def update(self,instance,validated_data):
        try:
            instance.update_slot(**validated_data)
        except DjangoValidationError as err:
            raise ValidationError(err.message)
        return instance

    def validate_batch(self,batch):
        adminProfile = self.context.get('request').profile
        if batch.admin != adminProfile:
            raise ValidationError(response.noBatchOwnershipResponse())
        return batch

    def validate_faculty(self,faculty):
        adminProfile = self.context.get('request').profile
        if faculty.admin != adminProfile:
            raise ValidationError(response.noFacultyOwnershipResponse())
        return faculty

    def validate(self,validated_data):               
        startTime,endTime = itemgetter('start_time','end_time')(validated_data)
        if startTime >= endTime:
            raise ValidationError(response.startTimeGreaterResponse())  
        return validated_data

    def to_representation(self, instance):
        newRep =  AdminSlotDisplaySerializer(instance).data
        return {'status': 1, 'data': newRep}


class SlotRetrieveSerializer(AdminSlotDisplaySerializer):
    
    class Meta(AdminSlotDisplaySerializer.Meta):
        fields = ['id','title', 'startTime', 'endTime','weekday','faculty']

    startTime = serializers.SerializerMethodField()
    endTime = serializers.SerializerMethodField()
    weekday = serializers.IntegerField()

    #Need 24 Hour format instead of 12 Hour format
    def get_startTime(self,instance):
        return instance.start_time.strftime('%H:%M')

    def get_endTime(self,instance):
        return instance.end_time.strftime('%H:%M')

    def to_representation(self, instance):
        response =  super().to_representation(instance)
        return {'status': 1, 'data': response}

""" Batch Serializers """

class BatchSerializer(serializers.ModelSerializer):
    """
    Used by list and create views.
    """
    class Meta:
        model = Batch
        fields = ['id', 'title', 'onboard_students', 'max_students']
        extra_kwargs = {'onboard_students': {'write_only': True},
                        'max_students': {'write_only': True}}

    id = serializers.CharField(source='uuid', read_only=True)

    def validate_title(self, title):
        admin_profile = self.context.get('request').profile
        if admin_profile.batch_set.filter(title__iexact=title).exists():
            raise ValidationError('Batch with same title already exists!')
        return title

    def validate_max_students(self, max_student):
        if max_student <= 0:
            raise ValidationError('Max Students has to be greater than 0!')
        return max_student

    def to_representation(self, instance):
        request = self.context.get('request')
        if request.method == 'POST':
            return {'status': 1, 'data': 'Batch created successfully!'}
        return super().to_representation(instance)


class BatchUpdateSerializer(BatchSerializer):
    """
    Used by Update view.
    """
    class Meta(BatchSerializer.Meta):
        extra_kwargs = {}

    def validate_title(self, title):
        #Dont check for uniqueness when current title equals previous title.
        if self.instance and title.lower() == self.instance.title.lower():
            return title
        return super().validate_title(title)

    def validate_max_students(self, max_student):
        super().validate_max_students(max_student)
        if self.instance and max_student < self.instance.total_students():
            raise ValidationError(
                'Max students can\'t be lower than current student count!')
        return max_student

    #TODO: Make case style same in create & update
    def to_representation(self, instance):
        response =  super().to_representation(instance)
        response['onboardStudents'] = response.pop('onboard_students')
        response['maxStudents'] = response.pop('max_students')
        return response



class BatchDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Batch
        fields = ['id', 'title', 'isActive', 'totalFaculties', 'totalStudents',
                  'totalClasses', 'weekdayData']

    id = serializers.CharField(source='uuid')
    isActive = serializers.BooleanField(source='active')
    totalStudents = serializers.IntegerField(source='total_students')
    totalClasses = serializers.IntegerField(source='total_classes')
    totalFaculties = serializers.SerializerMethodField()
    weekdayData = serializers.SerializerMethodField()

    def get_totalFaculties(self,instance):
        return instance.getAssignedFaculties().count()

    def get_weekdayData(self,instance):
        all_slots = instance.connected_slots.select_related('faculty')\
            .order_by('weekday','start_time')
        
        return all_slots.serialize_and_group_by_weekday(serializer = AdminSlotDisplaySerializer,
                                                        context=self.context)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        return {'status':1,'data':response}


class BatchFacultySerializer(serializers.ModelSerializer):
    """
    Used Internally by BatchListDetailSerializer
    """
    class Meta:
        model = FacultyProfile
        fields = ['name','image']
        
    image = serializers.SerializerMethodField()

    def get_image(self,instance):
        request = self.context.get('request')
        return get_image(request,instance.user.thumbnail)


class BatchListDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Batch
        fields = ['id', 'title', 'isActive', 'totalFaculties', 'totalStudents',
                  'totalClasses', 'onboardStudents', 'maxStudents', 'inviteLink',
                  'created', 'assignedFaculties']

    id = serializers.CharField(source='uuid')
    isActive = serializers.BooleanField(source='active')
    totalStudents = serializers.IntegerField(source='total_students')
    totalClasses = serializers.IntegerField(source='total_classes')
    totalFaculties = serializers.SerializerMethodField()
    inviteLink = serializers.CharField(source='uuid')
    onboardStudents = serializers.BooleanField(source='onboard_students')
    maxStudents = serializers.IntegerField(source='max_students')
    created = serializers.SerializerMethodField()
    assignedFaculties = serializers.SerializerMethodField()

    def get_totalFaculties(self, instance):
        return instance.getAssignedFaculties().count()

    def get_created(self,instance):
        return instance.created.strftime('%d %b %Y')

    def get_assignedFaculties(self,instance):
        queryset = instance.getAssignedFaculties()
        return BatchFacultySerializer(queryset,context=self.context,many=True).data


class BatchSlotSerializer(serializers.ModelSerializer):
    """
    Used Internally by BatchDeletePreviewSerializer
    """
    class Meta:
        model = Slot
        fields = ['title','startTime', 'endTime', 'weekday', 'facultyName']

    startTime = serializers.CharField(source='get_start_time')
    endTime = serializers.CharField(source='get_end_time')
    weekday = serializers.CharField(source='get_weekday_string')
    facultyName = serializers.CharField(source='faculty.name', read_only=True)


class BatchStudentSerializer(serializers.ModelSerializer):
    """
    Used Internally by BatchDeletePreviewSerializer
    """
    class Meta:
        model = StudentProfile
        fields = ['name','image']

    image = serializers.SerializerMethodField()

    def get_image(self,instance):
        request = self.context.get('request')
        return get_image(request,instance.user.thumbnail)


class BatchDeletePreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['slotPreview', 'studentPreview']

    slotPreview = BatchSlotSerializer(
        many=True, read_only=True, source='connected_slots')
    studentPreview = BatchStudentSerializer(
        many=True, read_only=True, source='student_profiles')

""" Student Serializers """
   
class StudentIdSerializer(serializers.Serializer): 
    students = serializers.ListField(child=serializers.UUIDField(),allow_empty=True)


class StudentDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentProfile
        fields = ['id','name','image','joined','email']

    id = serializers.CharField(source='uuid')
    image = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email')

    def get_image(self, instance):
        request = self.context.get('request')
        return get_image(request,instance.user.thumbnail)

    def get_joined(self,instance):
        return instance.joined.strftime('%d %b %Y')

""" Broadcast Serializers """

class BroadcastTargetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Batch
        fields = ['label', 'value']

    label = serializers.SerializerMethodField()
    value = serializers.CharField(source='uuid')

    def get_label(self, instance):
        totalStudents = instance.students_count
        totalFaculties = instance.getAssignedFaculties()\
                            .filter(status=FacultyProfile.VERIFIED).count()
        return f'{instance.title} , {totalStudents} students , {totalFaculties} faculties'


class BroadcastSerializer(serializers.ModelSerializer):

    class Meta:
        model = Broadcast
        fields = ['text', 'target']

    EVERYONE = 'EVERYONE'
    STUDENT = 'STUDENT'
    FACULTY = 'FACULTY'
    filter_by_batch = False

    target = serializers.CharField()
    text = serializers.CharField(style={'base_template': 'textarea.html'})

    def create(self, validated_data):
        text, sender, receivers = itemgetter('text', 'sender', 'receivers')(validated_data)
        broadcast = Broadcast.objects.create(sender=sender,text=text)
        print("\n",receivers,"\n")
        broadcast.receivers.add(*receivers)       
        return broadcast

    #TODO:Common : Move to model
    def validate_text(self, text):
        if len(text) > 500:
            raise ValidationError('Text cant exceed 500 characters!')
        return text

    def validate(self,validated_data):
        target = validated_data['target']
        user = self.context.get('request').profile

        try:
            target = UUID(target)
            batch = Batch.objects.get(admin=user, uuid=target)
            self.filter_by_batch = True
        except (ValueError, Batch.DoesNotExist):
            pass

        if target not in {self.EVERYONE, self.STUDENT, self.FACULTY} and not self.filter_by_batch:
            raise ValidationError(
                f'Target can only be {self.EVERYONE}/{self.STUDENT}/{self.FACULTY}/Valid Batch ID !')
        
        receivers = []
        #Add all the relevant faculties receivers
        if target in {self.EVERYONE,self.FACULTY} or self.filter_by_batch:
            allFaculties = user.connected_faculties.filter(
                status=FacultyProfile.VERIFIED)

            if self.filter_by_batch:
                allFaculties = allFaculties.filter(slots__batch=batch).distinct()

            allFaculties = [faculty.user.id for faculty in allFaculties]
            receivers.extend(allFaculties)

        #Add all the relevant students receivers
        if target in {self.EVERYONE,self.STUDENT} or self.filter_by_batch:    
            if self.filter_by_batch:
                allStudents = list(batch.student_profiles.values_list('user', flat=True))
            else:               
                allBatches = user.batch_set.values_list('id')
                allStudents = [student.user.id 
                for student in StudentProfile.objects.filter(batch__in=allBatches)]
                
            receivers.extend(allStudents)

        if not receivers:
            raise ValidationError('No Recipients exist to receive this broadcast!')
        
        validated_data['receivers'] = receivers
        return validated_data

    def to_representation(self, instance):
        sent_to = instance.receivers.count()
        return {'status': 1, 'data': f'Broadcast sent to {sent_to} people.'}
        
