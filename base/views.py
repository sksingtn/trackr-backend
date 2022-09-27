from datetime import time
from collections import defaultdict

from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework import status
from rest_framework.parsers import FormParser,MultiPartParser

from .serializers import UserSerializer,ActivitySerializer,UserImageSerializer
from base.models import Activity, CustomUser,Broadcast, Message
from base.utils import get_elapsed_string,get_user_profile,get_image
from AdminUser.models import AdminProfile
from FacultyUser.models import FacultyProfile
from StudentUser.models import StudentProfile
from .pagination import EnhancedPagination


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

        except CustomUser.DoesNotExist:
            raise ValidationError('The Email/Password combination is incorrect!')

        except AssertionError as e:
            raise ValidationError(str(e))

        token,_ = Token.objects.get_or_create(user=base_user)
        user_info = {'token':token.key,'role':base_user.user_type}

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
    #TODO:Change from UTC when showing
    permission_classes = [IsAuthenticated]

    def get(self, request):  
        user = request.user
        profile = get_user_profile(user)
        showDetail = request.query_params.get('detail', '').lower() == 'true'

        userInfo = defaultdict(dict)
        userInfo['basics'] = {'name':profile.name,'userType':user.user_type,
                             'isActive':isinstance(profile,AdminProfile) or profile.is_active()}
        if not showDetail:
            userInfo['basics']['image'] = get_image(request,user.thumbnail)
        else:
            userInfo['basics']['image'] = get_image(request,user.profile_image)

            userInfo['details'] = {'email':user.email,
                                  'joined':profile.joined.strftime('%d %b %Y')}
            
            if isinstance(profile,AdminProfile):
                userInfo['details']['timezone'] = str(profile.timezone)

            elif isinstance(profile,FacultyProfile) and profile.is_active():           
                userInfo['details']['timezone'] = str(profile.admin.timezone)
                userInfo['details']['admin'] = profile.admin.name
                userInfo['preferences']['sendNotification'] = profile.receive_email_notification

            elif isinstance(profile,StudentProfile) and profile.is_active():
                userInfo['details']['timezone'] = str(profile.batch.admin.timezone)
                userInfo['details']['admin'] = profile.batch.admin.name
                userInfo['details']['batch'] = profile.batch.title
                userInfo['preferences']['sendNotification'] = profile.receive_email_notification

        return Response({'status': 1, 'data': userInfo}, status=status.HTTP_200_OK) 


class UploadProfileImageView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    serializer_class = UserImageSerializer

    def post(self,request):
        serializer = UserImageSerializer(data=request.data, instance=request.user)
        oldImg = request.user.profile_image
        oldThumbnail = request.user.thumbnail

        serializer.is_valid(raise_exception=True)

        #Delete old Images if any.
        for img in (oldImg,oldThumbnail):
            if bool(img):
                img.delete()

        serializer.save()
        return Response({'status':1,'data':get_image(request,request.user.profile_image)},status=status.HTTP_201_CREATED)


class ToggleNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        user = request.user
        if user.user_type not in {CustomUser.FACULTY,CustomUser.STUDENT}:
            raise ValidationError('Only applicable to Faculty/Student users!')

        profile = get_user_profile(user)

        if not profile.is_active():
            raise ValidationError('Your Account has been deleted by the admin!')

        profile.receive_email_notification = not profile.receive_email_notification
        profile.save()

        return Response({'status':1,'data':profile.receive_email_notification},
                        status=status.HTTP_200_OK)



class ShowActivity(ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = EnhancedPagination
    serializer_class = ActivitySerializer

    def get_queryset(self):
        return self.request.user.activities.order_by('-created')

    def paginate_queryset(self, queryset):
        activityList = self.paginator.paginate_queryset(queryset, self.request, view=self)
        
        #Update read status for read activities in current page.
        unread = [activity.id for activity in activityList if not activity.read]
        if unread:
            Activity.objects.filter(id__in=unread).update(read=True)

        return activityList
        
    def get_paginated_response(self, data):
        unreadCount = self.request.user.activities.filter(read=False).count()
        return self.paginator.get_paginated_response(data,unreadCount=unreadCount)
   

class ShowBroadcast(APIView):

    SENT = 'SENT'
    RECEIVED = 'RECEIVED'
    permission_classes = [IsAuthenticated]

    def serialize(self,queryset):
        """
        Custom serialization because data has 2 perspectives i.e sent and received,
        and it gets too complex with DRF serializer.
        """
        jsonData = []
        for broadcast in queryset:
            serialized = {}
            if broadcast.sender == self.request.user:
                serialized['type'] = self.SENT                
                receivers = []
                for message in broadcast.message_set.all():
                    receiver = message.receiver
                    img = get_image(self.request,receiver.thumbnail)
                    receivers.append({'email':receiver.email,
                                      'type':receiver.user_type,
                                      'image':img,
                                      'read':message.read})
                serialized['receivers'] = receivers

            else:
                serialized['type'] = self.RECEIVED
                sender = broadcast.sender
                profile_info = {'email': sender.email, 'type': sender.user_type,
                                'image': get_image(self.request,sender.thumbnail)}
                serialized['sentBy'] = profile_info
                serialized['sentTo'] = broadcast.message_set.count()
                serialized['read'] = broadcast.message_set.get(receiver=self.request.user).read

            serialized['text'] = broadcast.text
            serialized['created'] = get_elapsed_string(broadcast.created)
            jsonData.append(serialized)

        return jsonData

    def get(self,request):     
        currentUser = request.user
        filter_by_type = request.query_params.get('filter','').upper()
   
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
            if filter_by_type == self.SENT:
                all_broadcasts = currentUser.sent_broadcasts.all()
            elif filter_by_type == self.RECEIVED:
                all_broadcasts = currentUser.received_broadcasts.all()
            else:
                all_broadcasts = Broadcast.objects.filter(Q(sender=currentUser)|Q(receivers=currentUser)).distinct()
        else:
            raise ValidationError("Corrupt User!")
                
        
        all_broadcasts = all_broadcasts.select_related('sender').prefetch_related('message_set__receiver')\
                        .order_by('-created')
        pagination = EnhancedPagination()
        all_broadcasts = pagination.paginate_queryset(all_broadcasts, request)
        serialized_data = self.serialize(all_broadcasts)

        #Calculate unread messages & update the read status of already read messages.
        unreadCount = None
        if (currentUser.user_type == CustomUser.STUDENT) or  \
            (currentUser.user_type == CustomUser.FACULTY  and filter_by_type !=self.SENT):

            read_msgs = Message.objects.filter(broadcast__in=all_broadcasts,receiver=currentUser,read=False)    
            read_msgs.update(read=True)
            
            unreadCount = Message.objects.filter(receiver=currentUser, read=False).count()
                      
        return pagination.get_paginated_response(serialized_data,unreadCount=unreadCount)


class MarkActivityAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        unread = Activity.objects.filter(user=request.user,read=False)
        unreadCount = unread.count()

        if unreadCount == 0:
            msg = 'All Activities are already read!'
        else:
            unread.update(read=True)
            msg = f'{unreadCount} activities marked as read!'

        return Response({'status':1,'data':msg},status=status.HTTP_200_OK)


class MarkBroadcastAsReadView(APIView):
    #TODO:Broadcast for deleted users
    permission_classes = [IsAuthenticated]

    def post(self,request):
        user = request.user

        #Admin users dont receive broadcasts.
        if user.user_type not in {CustomUser.FACULTY,CustomUser.STUDENT}:
            raise ValidationError('Only applicable to Faculty/Student users!')

        unread = Message.objects.filter(receiver=user,read=False)
        unreadCount = unread.count()

        if unreadCount == 0:
            msg = 'All Broadcasts are already read!'
        else:
            unread.update(read=True)
            msg = f'{unreadCount} broadcasts marked as read!'

        return Response({'status':1,'data':msg},status=status.HTTP_200_OK)






