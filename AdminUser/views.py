from collections import defaultdict

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView,ListCreateAPIView,ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.utils import timezone

from . import serializers as ser
from base.models import CustomUser,AdminProfile,FacultyProfile,Batch,Slot
from StudentUser.models import StudentProfile
from .permissions import IsAdmin
from .pagination import ModifiedPageNumberPagination
from base.utils import WEEKDAYS
from .utils import StudentBatchMixin,FacultyMixin,BatchMixin
from FacultyUser.exception import Error as FacultyError


#Subclass from a more specific subclass in the end.
class SignupView(APIView):
    """ Signup for Admins """
    serializer_class = ser.SignupSerializer
    permission_classes = [AllowAny]
    def post(self,request):
        data = self.serializer_class(data=request.data)
        data.is_valid(raise_exception=True)

        username = data.validated_data.pop('name')
        new_user = data.save()

        #Create A Token
        Token.objects.create(user=new_user)
        #Associate With an Admin Profile
        AdminProfile.objects.create(user=new_user,name=username)

        return Response({'status':1,'message':'User Successfully created!'},status=status.HTTP_201_CREATED)


class FacultyView(APIView):
    """
    Shows All the Connected Faculties or a subset (on search) on GET,
    Invite functionality via POST i.e send an inviation mail when email 
    is given otherwise simply add a blank user.
    """
    serializer_class = ser.FacultySerializer
    permission_classes = [IsAuthenticated,IsAdmin]

    def get(self,request):  
    
        connected_faculties = request.profile.invited_faculties.select_related('user').order_by('name')
        search = request.query_params.get('q')
        detail = request.query_params.get('detail','0')
        detail = True if detail == '1' else False

        if search:
            connected_faculties = connected_faculties.filter(name__icontains=search)
        
        if detail:
            serializer = ser.FacultyDetailSerializer
        else:
            serializer = ser.FacultySerializer
        
        paginator = ModifiedPageNumberPagination()
        page = paginator.paginate_queryset(connected_faculties, request)
        serializer = serializer(page, many=True,context={'request':request})
        return paginator.get_paginated_response(serializer.data)

    def post(self,request):
        data = self.serializer_class(data=request.data, context={'profile': self.request.profile})
        data.is_valid(raise_exception=True)
        data.save(admin=request.profile)
        return Response({'status':1,'data':'User Successfully Invited!'},status=status.HTTP_201_CREATED)


class FacultyDeleteView(FacultyMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self,request,faculty_id):
        #Delete Preview
        faculty = self.get_faculty(faculty_id)
        delete_preview = faculty.delete_preview()
        return Response({'status':1,'data':delete_preview},status=status.HTTP_200_OK)

    def delete(self,request,faculty_id):
        faculty =self.get_faculty(faculty_id)
        deleted_slots = faculty.delete_profile()
        msg = 'Successfully deleted faculty'
        if deleted_slots:
            msg += f' along with {deleted_slots} associated slots'

        return Response({'status': 1, 'data': msg}, status=status.HTTP_200_OK)


class FacultyInviteView(FacultyMixin,APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ser.FacultyEmailSerializer
    def put(self,request,faculty_id):
        faculty = self.get_faculty(faculty_id)
        is_overriden = faculty.status == faculty.INVITED

        data = self.serializer_class(data=request.data)
        data.is_valid(raise_exception=True)

        try:
            faculty.add_user(email=data.validated_data['email'])
        except FacultyError as err:
            raise ValidationError(str(err))

        if is_overriden:
            msg = 'Email Invite successfully sent to updated address'
        else:
            msg = 'User Successfully Added & Invited!'

        return Response({'status': 1, 'data':msg}, status=status.HTTP_200_OK)
        

class FacultyReInviteView(FacultyMixin,APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def put(self,request,faculty_id):
        faculty = self.get_faculty(faculty_id)

        try:
            faculty.send_invite()
        except FacultyError as err:
            raise ValidationError(str(err))

        return Response({'status': 1, 'data': 'Email Invite sent successfully!'}, status=status.HTTP_200_OK)


class SlotView(APIView):
    """ Handles Creation,Updation & Deletion of Slots """
    serializer_class = ser.SlotSerializer
    permission_classes = [IsAuthenticated,IsAdmin]

    def post(self,request,slot_id=None):
        data = self.serializer_class(data=request.data,context={'profile':self.request.profile})
        data.is_valid(raise_exception=True)
        data.save()
        return Response({'status':1,'data':data.data},status=status.HTTP_201_CREATED)

    def put(self, request, slot_id=None):

        #Move it to a common class method!
        #Making sure that requested slot is owned by current admin.
        try:
            slot = Slot.objects.get(pk=slot_id,batch__admin=self.request.profile)
        except Slot.DoesNotExist:
            raise ValidationError('Matching Slot does not exist')

        data = self.serializer_class(slot,data=request.data, context={'profile': self.request.profile})               
        data.is_valid(raise_exception=True)
        data.save(created = timezone.localtime())
        return Response({'status': 1, 'data': data.data}, status=status.HTTP_200_OK)

    def delete(self,request,slot_id=None):
        try:
            slot = Slot.objects.get(pk=slot_id,batch__admin=self.request.profile)
        except Slot.DoesNotExist:
            return Response({'status': 0, 'data': 'Matching Slot does not exist'})

        data = self.serializer_class(slot).data
        slot.delete()

        #Garbage collection of unused timing needed.

        return Response({'status': 1, 'data': data}, status=status.HTTP_200_OK)

       
class BatchView(APIView):
    """ Handles Creation,ListView & DetailView of Batches """
    permission_classes = [IsAuthenticated,IsAdmin]
    serializer_class = ser.SimpleBatchSerializer

    def get(self,request,batch_id=None):

        if batch_id is None:
            all_batches = self.request.profile.batch_set.all()
            data = ser.SimpleBatchSerializer(all_batches,many=True)
            return Response({'status':1,'data':data.data})

        #Create a mixin for this.
        try:
            batch = self.request.profile.batch_set.get(pk=batch_id)
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist')

        batchData = ser.BatchSerializer(batch).data

        all_slots = batch.connected_slots.select_related('timing', 'faculty')\
                    .order_by('timing__start_time')
        
        jsonData = all_slots.serialize_and_group_by_weekday(serializer=ser.SlotSerializer)

        return Response({'status': 1, 'data': {**batchData, "weekdayData": jsonData}}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if kwargs.get('batch_id'):
            raise ValidationError('/batch_id/ not needed for POST method!')
        data = ser.SimpleBatchSerializer(data=request.data, context={'profile': self.request.profile})

        data.is_valid(raise_exception=True)
        data.save(admin=self.request.profile)
        return Response({'status':1,'data':data.data},status=status.HTTP_201_CREATED)


class BatchDetailView(ListAPIView):
    pagination_class = ModifiedPageNumberPagination
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ser.BatchDetailSerializer

    def get_queryset(self):
        all_batches = self.request.profile.batch_set.order_by('title')
        search = self.request.query_params.get('q')

        if search:
            all_batches = all_batches.filter(title__icontains=search)
        return all_batches


class BatchEditView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ser.BatchEditSerializer

    def put(self,request,batch_id):
        #Create a mixin for this.
        try:
            batch = self.request.profile.batch_set.get(pk=batch_id)
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist')

        data = self.serializer_class(batch,data=request.data,context={'profile': request.profile})
        data.is_valid(raise_exception=True)
        data.save()

        return Response({'status':1,'data':data.data},status=status.HTTP_200_OK)

class BatchDeleteView(BatchMixin,APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self,request,batch_id):
        batch = self.get_batch(batch_id)
        delete_preview = batch.delete_preview()
        return Response({'status': 1, 'data': delete_preview}, status=status.HTTP_200_OK)

    def delete(self,request,batch_id):
        batch = self.get_batch(batch_id)
        batch.delete()
        return Response({'status': 1, 'data': 'Deleted Batch success!'}, status=status.HTTP_200_OK)


class ToggleView(APIView):
    permission_classes = [IsAuthenticated,IsAdmin]

    #Maybe make this a mixin
    def get_batch(self,batch_id):
        try:
            batch = self.request.profile.batch_set.get(pk=batch_id)
            return batch
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist')

    @staticmethod
    def toggle(instance):
        instance.active = not instance.active
        instance.save()
        return instance.active

    def get(self,request,batch_id=None):       
        if batch_id:
            batch = self.get_batch(batch_id)
            value = batch.active
        else:
            value = self.request.profile.active

        return Response({'status':1,'data':{'active':value}},status=status.HTTP_200_OK)

    def put(self,request,batch_id=None):
        if batch_id:
            batch = self.get_batch(batch_id)           
            value = self.toggle(batch)
        else:
            value = self.toggle(self.request.profile)

        return Response({'status':1,'data':{'active':value}},status=status.HTTP_200_OK)


class StudentListView(StudentBatchMixin,APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ser.StudentDetailSerializer

    def get(self,request,batch_id):
        batch = self.get_batch(batch_id)
        all_students = batch.student_profiles.select_related('user').order_by('joined')

        search = request.query_params.get('q')
        if search:
            all_students = all_students.filter(name__icontains=search)

        paginator = ModifiedPageNumberPagination()
        page = paginator.paginate_queryset(all_students, request)
        serializer = self.serializer_class(
            page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class StudentMoveView(StudentBatchMixin,APIView):   
    permission_classes = [IsAuthenticated,IsAdmin]
    serializer_class = ser.StudentIdSerializer

    def put(self,request,source_batch_id,destination_batch_id):
        data = self.serializer_class(data=request.data)
        data.is_valid(raise_exception=True)
        student_list = data.validated_data['students']

        destination_batch = self.get_batch(destination_batch_id)
        source_batch, all_students = self.get_student_queryset(
                                    source_batch_id, student_list)
        
        total_students = all_students.count()
        all_students.update(batch=destination_batch)
        msg = f'Successfully moved {total_students} students from {source_batch.title} to {destination_batch.title}'

        return Response({'status':1,'data':msg},status=status.HTTP_200_OK)


class StudentDeleteView(StudentBatchMixin,APIView):
    permission_classes = [IsAuthenticated,IsAdmin]
    serializer_class = ser.StudentIdSerializer

    def put(self,request,batch_id):
        data = self.serializer_class(data=request.data)
        data.is_valid(raise_exception=True)
        student_list = data.validated_data['students']

        batch, all_students = self.get_student_queryset(
                                        batch_id, student_list)

        total_students = all_students.count()
        all_students.update(batch=None)
        msg = f'Successfully deleted {total_students} students from {batch.title}'

        return Response({'status':1,'data':msg},status=status.HTTP_200_OK)

        






        
        

        
