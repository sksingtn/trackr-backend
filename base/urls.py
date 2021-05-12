from django.urls import path
from . import views as view


urlpatterns = [
    path('login/', view.CommonLoginView.as_view(),name='login'),
    path('logout/', view.CommonLogoutView.as_view(),name='logout'),
    path('profile/', view.UserProfileView.as_view(),name='profile'),

    path('show-activity/', view.ShowActivity.as_view(),name='show-activity'),
    path('show-broadcast/', view.ShowBroadcast.as_view(),name='show-broadcast')
    
]