from re import search
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q,Count
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework import serializers, status

from .serializers import UserSerializer,BroadcastSerializer
from base.models import CustomUser,Broadcast, Message
from base.utils import get_elapsed_string,get_user_profile
from AdminUser.models import AdminProfile
from FacultyUser.models import FacultyProfile
from StudentUser.models import StudentProfile
from .pagination import BroadcastPagination

class CommonLoginView(APIView):

    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def post(self,request):
        data = self.serializer_class(data=request.data)
        data.is_valid(raise_exception=True)

        try:
            base_user = CustomUser.objects.get(email=data.validated_data['email'])
            if not base_user.check_password(data.validated_data['password']):
                raise CustomUser.DoesNotExist

            assert base_user.user_type is not None,'Invalid User!'

            #Maybe another validation to confirm the user_type?

        except CustomUser.DoesNotExist:
            raise ValidationError('The Email/Password combination is incorrect!')

        except AssertionError as e:
            raise ValidationError(str(e))

        token,_ = Token.objects.get_or_create(user=base_user)
        user_info = {'key':token.key,'type':base_user.user_type}

        return Response({'status':1,'data':user_info},status=status.HTTP_200_OK)


class CommonLogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self,request):
        try:
            request.auth.delete()
        except Exception:
            raise ValidationError('Something went wrong!')
        return Response({'status': 1, 'data': 'User logged out successfully!'}, status=status.HTTP_200_OK)


class UserProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):       
        user_type = request.user.user_type
        user_info = {}

        try:
            if user_type == request.user.ADMIN:
                profile = AdminProfile.objects.get(user=request.user)
                
            elif user_type == request.user.FACULTY:
                profile = FacultyProfile.objects.get(user=request.user)
                user_info['account_active'] = profile.is_active()

                user_info.setdefault('invited_by',None)
                if user_info['account_active']:
                    user_info['invited_by'] = profile.admin.name

            elif user_type == request.user.STUDENT:                
                profile = StudentProfile.objects.get(user=request.user)
                user_info['account_active'] = profile.is_active()

                user_info.update({'invited_by':None,'batch':None})
                if user_info['account_active']:
                    user_info['invited_by'] = profile.batch.admin.name
                    user_info['batch'] = profile.batch.title
            else:
                raise ObjectDoesNotExist

            #Common Fields
            user_info['name'] = profile.name
            user_info['email'] = profile.user.email
            user_info['image'] = request.build_absolute_uri(profile.image.url)
            user_info['type'] = user_type
                

        except ObjectDoesNotExist:
            raise ValidationError('Corrupt User!')

        return Response({'status': 1, 'data': user_info}, status=status.HTTP_200_OK)


class ShowActivity(APIView):
    pass


#Testing needed
class ShowBroadcast(APIView):

    SENT = 'SENT'
    RECEIVED = 'RECEIVED'
    permission_classes = [IsAuthenticated]

    def serialize(self,queryset):
        """
        Custom serialization because data had 2 perspectives,
        and it was getting two complex for the Serializer class.
        """
        jsonData = []
        for broadcast in queryset:
            serialized = {}
            receivers = broadcast.receivers.count()
            if broadcast.sender == self.request.user:
                serialized['type'] = self.SENT
                serialized['received_by'] = receivers
                serialized['read_by'] = broadcast.message_set.filter(read=True).count()
            else:
                serialized['type'] = self.RECEIVED
                profile = get_user_profile(broadcast.sender)
                profile_info = {'name': profile.name, 'type': broadcast.sender.user_type,
                                'image': self.request.build_absolute_uri(profile.image.url)}
                serialized['sent_by'] = profile_info
                serialized['sent_to'] = receivers
                serialized['read'] = broadcast.message_set.get(receiver=self.request.user).read

            serialized['text'] = broadcast.text
            serialized['created'] = get_elapsed_string(broadcast.created)
            jsonData.append(serialized)

        return jsonData

    def get(self,request):     
        currentUser = request.user
        filter_by_type = request.query_params.get('type','').upper()

        if currentUser is None:
            raise ValidationError('Corrupt User!')

        if filter_by_type:
            if currentUser.user_type != CustomUser.FACULTY:
                raise ValidationError('Filter is only applicable for Faculty Users!')

            if filter_by_type not in {self.SENT,self.RECEIVED}:
                raise ValidationError('Filter parameter can only either be SENT/RECEIVED !')

        if currentUser.user_type == CustomUser.ADMIN:
            all_broadcasts = currentUser.sent_broadcasts.all()

        elif currentUser.user_type == CustomUser.STUDENT:
            all_broadcasts = currentUser.received_broadcasts.all()

        elif currentUser.user_type == CustomUser.FACULTY:
            #Lazy loaded so not an issue
            sent_broadcasts = currentUser.sent_broadcasts.all()
            received_broadcasts = currentUser.received_broadcasts.all()

            if filter_by_type == self.SENT:
                all_broadcasts = sent_broadcasts
            elif filter_by_type == self.RECEIVED:
                all_broadcasts = received_broadcasts
            else:
                all_broadcasts = Broadcast.objects.filter(Q(sender=currentUser)|Q(receivers=currentUser)).distinct()
                
        #Maybe specific for each
        all_broadcasts = all_broadcasts.select_related('sender').prefetch_related('receivers')\
                        .order_by('-created')
        pagination = BroadcastPagination()
        all_broadcasts = pagination.paginate_queryset(all_broadcasts, request)
        serialized_data = self.serialize(all_broadcasts)

        all_unread = None
        if (currentUser.user_type == CustomUser.STUDENT) or  \
            (currentUser.user_type == CustomUser.FACULTY  and filter_by_type !=self.SENT):

            read_msgs = Message.objects.filter(broadcast__in=all_broadcasts,receiver=currentUser,read=False)    
            read_msgs.update(read=True)
            
            all_unread = Message.objects.filter(receiver=currentUser, read=False).count()
            
            
        return pagination.get_paginated_response(serialized_data,unread=all_unread)






