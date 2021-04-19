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
from .permissions import IsAdmin
from .pagination import ModifiedPageNumberPagination
from base.utils import WEEKDAYS



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
        #Test and replace by request.profile.invited_faculties.all().order_by('name')    
        connected_faculties = FacultyProfile.objects.filter(admin=request.profile).order_by('name')
        search = request.query_params.get('q')
        if search:
            connected_faculties = connected_faculties.filter(name__icontains=search)
        
        paginator = ModifiedPageNumberPagination()
        page = paginator.paginate_queryset(connected_faculties, request)
        serializer = self.serializer_class(page, many=True,context={'request':request})
        return paginator.get_paginated_response(serializer.data)



    def post(self,request):
        data = self.serializer_class(data=request.data, context={'profile': self.request.profile})
        data.is_valid(raise_exception=True)
        data.save(admin=request.profile)
        return Response({'status':1,'data':'User Successfully Invited!'},status=status.HTTP_201_CREATED)


class SlotView(APIView):
    """ Handles Creation,Updation & Deletion of Slots """
    serializer_class = ser.CreateSlotSerializer
    permission_classes = [IsAuthenticated,IsAdmin]

    def post(self,request,slot_id=None):
        data = self.serializer_class(data=request.data,context={'profile':self.request.profile})
        data.is_valid(raise_exception=True)
        created_slot = data.save()
        data = ser.SlotSerializer(created_slot)

        return Response({'status':1,'data':data.data},status=status.HTTP_201_CREATED)

    def put(self, request, slot_id=None):

        """ Make sure that requested slot is owned by current admin """
        try:
            slot = Slot.objects.get(pk=slot_id,batch__admin=self.request.profile)
        except Slot.DoesNotExist:
            raise ValidationError('Matching Slot does not exist')

        data = self.serializer_class(slot,data=request.data, context={'profile': self.request.profile})               
        data.is_valid(raise_exception=True)
        updated_slot = data.save(created = timezone.now())
        data = ser.SlotSerializer(updated_slot)

        return Response({'status': 1, 'data': data.data}, status=status.HTTP_200_OK)

    def delete(self,request,slot_id=None):
        try:
            slot = Slot.objects.get(pk=slot_id,batch__admin=self.request.profile)
        except Slot.DoesNotExist:
            return Response({'status': 0, 'data': 'Matching Slot does not exist'})

        data = ser.SlotSerializer(slot).data
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
        try:
            batch = self.request.profile.batch_set.get(pk=batch_id)
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist')

        data = ser.BatchSerializer(batch).data
        connected_slots = ser.SlotSerializer(batch.connected_slots.all().order_by('timing__start_time'),many=True)

        #Grouping All slots by their Weekday
        weekday_dict = defaultdict(list)
        for item in connected_slots.data:
            weekday_dict[item.pop('weekday')].append(item)

        #Fill the empty weekdays with empty list.
        remaining = ({}.fromkeys(set(WEEKDAYS).difference(weekday_dict.keys()),[]))
        weekday_dict.update(remaining)

        #Sort them by weekday
        weekday_dict = dict(sorted(weekday_dict.items(),key=lambda x : WEEKDAYS.index(x[0])))

        return Response({'status':1,'data':{**data,"weekdayData":weekday_dict}},status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if kwargs.get('batch_id'):
            raise ValidationError('/batch_id/ not needed for POST method!')
        data = ser.SimpleBatchSerializer(data=request.data, context={'profile': self.request.profile})

        data.is_valid(raise_exception=True)
        data.save(admin=self.request.profile)
        return Response({'status':1,'data':data.data},status=status.HTTP_201_CREATED)
        

        
