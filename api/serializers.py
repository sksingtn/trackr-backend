from rest_framework import serializers
from base.models import CustomUser,FacultyProfile,Slot,SlotInfo,Schedule
from operator import itemgetter as fetch
from django.db.models import Q
from datetime import datetime,date
from django.utils import timezone


class SignupSerializer(serializers.ModelSerializer):

    name = serializers.CharField(write_only=True)

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
        if email:
            invited_user = CustomUser(email=email)
            invited_user.set_unusable_password()
            invited_user.save()
            validated_data['user'] = invited_user

            #Send An Invite Link

        return FacultyProfile.objects.create(**validated_data)

    def get_image(self, instance):
        request = self.context.get('request')
        return request.build_absolute_uri(instance.image.url)

    def validate_email(self,data) :
        if CustomUser.objects.filter(email=data).exists():
            raise serializers.ValidationError('User with this email already exists!')
        return data

    def validate_name(self,data):
        admin_profile = self.context.get('profile')
        if admin_profile.invited_faculties.filter(name__iexact=data).exists():
            raise serializers.ValidationError('You already have a faculty with same name!')
        return data






class SlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Slot
        fields = "__all__"


    def validate(self,validated_data):
        start,end = fetch('start_time','end_time')(validated_data)

        if start >= end:
            raise serializers.ValidationError('start time cant be greater than end time!')

        return validated_data


class CreateSlotSerializer(serializers.ModelSerializer):
    slot = SlotSerializer()

    class Meta:
        model = SlotInfo
        exclude = ['created']

    def create(self,validated_data):       
        validated_data['slot'],_ = Slot.objects.get_or_create(**validated_data.pop('slot'))
        
        return SlotInfo.objects.create(**validated_data)

    def update(self,instance,validated_data):
        old_slot = instance.slot
        validated_data['slot'], _ = Slot.objects.get_or_create(**validated_data.pop('slot'))
        
        for key,value in validated_data.items():
            setattr(instance,key,value)        
        instance.save()

        if old_slot != instance.slot and not old_slot.slotinfo_set.exists():
            old_slot.delete()

        return instance


    @staticmethod
    def overlap_checker(queryset,start_time,end_time,weekday):
        query = lambda time : Q(slot__start_time__lte=time,slot__end_time__gte=time)

        result = queryset.filter(slot__weekday=weekday).filter(
            query(start_time)|query(end_time))

        if result:
            return result.first()

    def validate(self,validated_data):
        
        admin_profile = self.context.get('profile')       
        faculty = validated_data.get('faculty')
        schedule = validated_data.get('schedule')

        if self.instance:

            #Cant Change batch of a slot
            if self.instance.schedule != schedule:
                raise serializers.ValidationError('Cant Move a slot to another batch!')
        
        #slot deletion handling in update

        #Making Sure that The Faculty/Schedule is connected to the current Admin
        for index,item in enumerate([faculty.admin,schedule.admin]):           
            if item != admin_profile:
                raise serializers.ValidationError(
                    f"The requested {'Batch' if index else 'Faculty'} was not {'added' if index else 'invited'} by current admin!")

        
        (_,start_time),(_,end_time),(_,weekday) = validated_data.get('slot').items()
        current_slot = [start_time,end_time,weekday]

        #Making Sure That there is no overlap between slots of the current schedule.
        queryset = schedule.connected_slots
        if self.instance:
            #Exclude Current Slot Timing from consideration
            queryset = queryset.exclude(pk=self.instance.id)

        overlapped_slots = self.overlap_checker(queryset,*current_slot)

        if overlapped_slots:
            raise serializers.ValidationError(f'Requested timing overlaps with {overlapped_slots.title} ({overlapped_slots.slot.start_time} - {overlapped_slots.slot.end_time})')


        #Making Sure that overlapping slots are not assigned to a faculty for a single admin.
        queryset = SlotInfo.objects.filter(faculty=faculty)
        if self.instance:
            #Exclude Current Slot Timing from consideration
            queryset = queryset.exclude(pk=self.instance.id)

        multiple_slots = self.overlap_checker(queryset,*current_slot)
        
        if multiple_slots:
            raise serializers.ValidationError(f'{faculty.name} already has a class in {multiple_slots.schedule.title} ({multiple_slots.slot.start_time} - {multiple_slots.slot.end_time})')
      
        
        return validated_data


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
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
        return instance.students.count()

    def get_verifiedFaculties(self,instance):
        total_faculties = set(FacultyProfile.objects.filter(slotinfo__schedule=instance))     
        verifiedFaculties = map(lambda profile: profile.status == "VERIFIED",total_faculties)                
        return f'{sum(verifiedFaculties)}/{len(total_faculties)}'

    def get_totalClasses(self,instance):
        return instance.connected_slots.count()


class SlotInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlotInfo
        fields = ['id','title', 'startTime', 'endTime',
                  'duration', 'created', 'facultyName','weekday']

    startTime = serializers.SerializerMethodField()
    endTime = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    facultyName = serializers.CharField(source='faculty.name')
    weekday = serializers.CharField(source='slot.weekday')

    def get_startTime(self,instance):
        return instance.slot.start_time.strftime('%I:%M %p')

    def get_endTime(self, instance):
        return instance.slot.end_time.strftime('%I:%M %p')

    def get_duration(self,instance):
        #Cant subtract time from time so combined both with a same date
        startTime = datetime.combine(date.today(), instance.slot.start_time)
        endTime = datetime.combine(date.today(), instance.slot.end_time)
        return f'{int((endTime-startTime).total_seconds()//60)} Mins'

    def get_created(self,instance):
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

        
class SimpleBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ['title', 'id']
        read_only_fields = ['id','active']

    def validate_title(self,title):
        admin_profile = self.context.get('profile')
        if admin_profile.schedule_set.filter(title__iexact=title).exists():
            raise serializers.ValidationError('Batch with same title already exists!')

        return title



    

        




    

