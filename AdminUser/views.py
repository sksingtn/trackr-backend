from django.db.models import Count

from rest_framework.views import APIView
from rest_framework.generics import (CreateAPIView,ListAPIView, ListCreateAPIView,
                                    RetrieveUpdateAPIView, RetrieveUpdateDestroyAPIView)
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.exceptions import ValidationError

from . import serializers as ser
from base.models import Activity
from .models import AdminProfile
from FacultyUser.models import FacultyProfile
from base.permissions import IsAuthenticatedWithProfile
from base.pagination import EnhancedPagination
from .mixins import (BatchToggleMixin, GetStudentMixin, GetFacultyMixin, 
                        GetBatchMixin,GetSlotMixin)
from FacultyUser.exception import Error as FacultyError



#TODO: Figure out how to verify email!
class SignupView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ser.AdminSignupSerializer

""" Faculty Views """

class FacultyView(ListCreateAPIView):
    """
    Shows All Faculties (detailed/normal) belonging to the admin on GET ,
    Invite functionality via POST i.e send an inviation mail when email 
    is given otherwise simply add a blank user.
    """
    serializer_class = ser.FacultySerializer
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    pagination_class = EnhancedPagination

    def get_queryset(self):
        connected_faculties = self.request.profile.connected_faculties.prefetch_related('teaches_in')\
            .select_related('user').order_by('-added')

        query = self.request.query_params.get('q')

        if query:
            connected_faculties = connected_faculties.filter(
                name__icontains=query)
        
        return connected_faculties

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ser.FacultySerializer

        showDetail = self.request.query_params.get('detail', '').lower() == 'true'
        if showDetail:
            return ser.FacultyDetailSerializer
        else:
            return ser.FacultySerializer

    def perform_create(self, serializer):
        serializer.save(admin=self.request.profile)


class FacultyStatsView(APIView):
    """
    Returns the faculty count (grouped by their status) .
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile

    def get(self,request):
        statusChoices = [choice for choice,_ in FacultyProfile.status_choices]
        #Initialize all status count to zero.
        groupByStatus = {}.fromkeys(statusChoices, 0)

        data = request.profile.connected_faculties.values('status')\
                        .annotate(count=Count('status'))
        
        data = {item['status']: item['count']
                for item in data.values('status', 'count')}
        
        groupByStatus.update(data)

        groupByStatus = {key.lower()+'Count': value
                         for key, value in groupByStatus.items()}

        groupByStatus['totalCount'] = sum(groupByStatus.values())

        return Response({'status': 1, 'data': groupByStatus}, status=status.HTTP_200_OK)


class FacultyDeleteView(GetFacultyMixin, APIView):
    """
    Used to delete a faculty account.
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile

    def delete(self,request,faculty_id):
        faculty =self.get_faculty(faculty_id)
        faculty.delete_profile()
        return Response({'status': 1, 'data': 'Faculty successfully deleted!'}, status=status.HTTP_200_OK)


class FacultyInviteView(GetFacultyMixin, APIView):
    """
    Used to add/overwrite email of UNVERIFIED/INVITED accounts.
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    serializer_class = ser.EmailSerializer

    def put(self,request,faculty_id):
        faculty = self.get_faculty(faculty_id)
        is_overriden = faculty.status == faculty.INVITED

        data = self.serializer_class(data=request.data)
        data.is_valid(raise_exception=True)

        email = data.validated_data['email']
        try:
            faculty.add_or_overwrite_user(email=email)
        except FacultyError as err:
            raise ValidationError(str(err))

        if is_overriden:
            msg = 'Email Invite successfully sent to the updated address!'
            activity=f"You updated invitation email of '{faculty.name}' FACULTY Account to {email}"
        else:
            msg = 'Email Successfully Added & Invite sent!'
            activity=f"You invited {email} to claim the '{faculty.name}' FACULTY Account"

        Activity.objects.create(user=request.user,text=activity)
        return Response({'status': 1, 'data':msg}, status=status.HTTP_200_OK)
        

class FacultyReInviteView(GetFacultyMixin, APIView):
    """
    Used to resend email invite to already INVITED accounts,
    limited to 1 per 24 hrs.
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile

    def put(self,request,faculty_id):
        faculty = self.get_faculty(faculty_id)

        try:
            faculty.send_invite()
        except FacultyError as err:
            raise ValidationError(str(err))

        return Response({'status': 1, 'data': 'Email Invite sent successfully!'}, status=status.HTTP_200_OK)



""" Slot Views """

class SlotView(CreateAPIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    serializer_class = ser.SlotCreateUpdateSerializer


class SlotRUDView(GetSlotMixin,RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    lookup_field = 'uuid'
    lookup_url_kwarg = 'slot_id'

    def get_object(self):
        return self.get_slot(self.kwargs['slot_id'])

    def get_serializer_class(self):      
        if self.request.method == 'GET':
            return ser.SlotRetrieveSerializer
        return ser.SlotCreateUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        uuid = instance.uuid
        instance.delete()
        return Response({'status':1,'data':uuid},status=status.HTTP_200_OK)


""" Batch Views """

class BatchListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    pagination_class = None
    serializer_class = ser.BatchSerializer

    def get_queryset(self):
        return self.request.profile.batch_set.all()

    def list(self,request,*args,**kwargs):
        response = super().list(request,*args,**kwargs)
        return Response({'status':1,'data':response.data},status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        Activity.objects.create(user=self.request.user,
        text=f"You created '{serializer.validated_data['title']}' batch")

        return serializer.save(admin=self.request.profile)


class BatchDetailedListView(ListAPIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    serializer_class = ser.BatchListDetailSerializer
    pagination_class = EnhancedPagination

    def get_queryset(self):
        all_batches = self.request.profile.batch_set.order_by('-created')
        search = self.request.query_params.get('q')

        if search:
            all_batches = all_batches.filter(title__icontains=search)
        return all_batches


class BatchDetailUpdateView(GetBatchMixin,RetrieveUpdateAPIView):
    """ Shows all the slots in the retrieve view """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    lookup_field = 'uuid'
    lookup_url_kwarg = 'batch_id'

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ser.BatchUpdateSerializer
        return ser.BatchDetailSerializer 

    def get_object(self):
        return self.get_batch(self.kwargs['batch_id'])


class BatchDeleteView(GetBatchMixin, APIView):
    """
    Shows Delete preview on GET,
    deletes batch on DELETE
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile

    def get(self,request,batch_id):
        batch = self.get_batch(batch_id)
        data = ser.BatchDeletePreviewSerializer(batch).data
        return Response({'status': 1, 'data': data}, status=status.HTTP_200_OK)

    def delete(self,request,batch_id):
        batch = self.get_batch(batch_id)
        batch.delete_batch()
        return Response({'status': 1, 'data': 'Deleted Batch successfully!'}, status=status.HTTP_200_OK)


class BatchToggleView(GetBatchMixin, APIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile

    def put(self,request,batch_id):      
        batch = self.get_batch(batch_id)           
        batch.active = not batch.active
        batch.save()    
        return Response({'status':1,'data':batch.active},status=status.HTTP_200_OK)


class BatchPauseAllView(BatchToggleMixin,APIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    action = False


class BatchResumeAllView(BatchToggleMixin,APIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    action = True

""" Student Views """

class StudentListView(GetBatchMixin, ListAPIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    serializer_class = ser.StudentDetailSerializer
    pagination_class = EnhancedPagination

    def get_queryset(self):
        batch = self.get_batch(self.kwargs['batch_id'])
        allStudents = batch.student_profiles.select_related('user')\
                        .order_by('joined')

        query = self.request.query_params.get('q')
        if query:
            allStudents = allStudents.filter(name__icontains=query)

        return allStudents


class StudentMoveView(GetStudentMixin,GetBatchMixin,APIView):   
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile

    def put(self,request,source_batch_id,destination_batch_id):
        data = ser.StudentIdSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        studentList = data.validated_data['students']

        sourceBatch = self.get_batch(source_batch_id)
        allStudents = self.get_student_queryset(sourceBatch, studentList)
        destinationBatch = self.get_batch(destination_batch_id)
    
        totalStudents = allStudents.count()
        #For all the affected student accounts
        Activity.bulk_create_from_queryset(queryset=allStudents,
        text=f'You have been moved from {sourceBatch.title} to {destinationBatch.title} by Admin')

        allStudents.update(batch=destinationBatch)

        #For the current Admin account
        msg = f'You moved {totalStudents} students from {sourceBatch.title} to {destinationBatch.title}'
        Activity.objects.create(user=request.user,text=msg)

        return Response({'status':1,'data':msg},status=status.HTTP_200_OK)


class StudentDeleteView(GetStudentMixin, GetBatchMixin, APIView):
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    
    def put(self,request,batch_id):
        data = ser.StudentIdSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        studentList = data.validated_data['students']

        batch = self.get_batch(batch_id)
        allStudents = self.get_student_queryset(batch, studentList)

        #For all the affected student accounts
        Activity.bulk_create_from_queryset(queryset=allStudents,
                              text=f'You account has been deleted by Admin!')

        totalStudents = allStudents.count()
        allStudents.update(batch=None)

        #For the current Admin account
        msg = f'You deleted {totalStudents} students from {batch.title}'
        Activity.objects.create(user=request.user,text=msg)

        return Response({'status':1,'data':msg},status=status.HTTP_200_OK)

""" Broadcast Views """

class BroadcastTargetView(ListAPIView):
    """
    Lists all the broadcast targets for the admin to choose from i.e
    all the available student,faculty groups that can receive the broadcast.
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    serializer_class = ser.BroadcastTargetSerializer
    pagination_class = None

    def get_queryset(self):
        return self.request.profile.batch_set\
            .annotate(students_count=Count('students', distinct=True))

    def list(self,request,*args,**kwargs):
        response = super().list(request,*args,**kwargs)

        totalFaculties = self.request.profile.connected_faculties\
                    .filter(status=FacultyProfile.VERIFIED).count()

        totalStudents = self.request.profile.batch_set.\
                        aggregate(students_count=Count('students', distinct=True))\
                            .pop('students_count')

        response.data.append({'label': f'All Students ({totalStudents})',
                              'value': 'STUDENT'})
        response.data.append({'label': f'All Faculties ({totalFaculties})',
                              'value': 'FACULTY'})
        response.data.append({'label': f'Everyone , {totalStudents} students, {totalFaculties} faculties',
                              'value': 'EVERYONE'})

        response.data = reversed(response.data)

        return Response({'status': 1, 'data': response.data}, status=status.HTTP_200_OK)


class BroadcastView(CreateAPIView):
    """
    Used to send broadcasts to students and faculty groups depending
    on the specified target.
    """
    permission_classes = [IsAuthenticatedWithProfile]
    required_profile = AdminProfile
    serializer_class = ser.BroadcastSerializer

    def perform_create(self, serializer):
        return serializer.save(sender=self.request.user)
