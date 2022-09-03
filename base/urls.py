from django.urls import path

from . import views as view


urlpatterns = [
    path('login/', view.CommonLoginView.as_view(),name='login'),
    path('logout/', view.CommonLogoutView.as_view(),name='logout'),
   
    path('profile/', view.UserProfileView.as_view(),name='profile'),
    path('toggle-notification/', view.ToggleNotificationView.as_view(),name='toggle-notification'),
    path('upload-profile-image/',view.UploadProfileImageView.as_view(),name='upload-profile-image'),

    path('show-activity/', view.ShowActivity.as_view(),name='show-activity'),
    path('show-broadcast/', view.ShowBroadcast.as_view(),name='show-broadcast'),
    path('mark-activity/',view.MarkActivityAsReadView.as_view(),name='mark-activity-as-read'),
    path('mark-broadcast/',view.MarkBroadcastAsReadView.as_view(),name='mark-broadcast-as-read'),

    #TODO:
    #forget password
    
    
]
