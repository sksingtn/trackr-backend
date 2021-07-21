from django.urls import path

from . import views as view


urlpatterns = [
    path('signup/', view.CreateAccountView.as_view()),

    ### Shows the assigned classes for the week
    path('timeline/', view.TimelineView.as_view()),

    ### Broadcast Messages to Students
    path('broadcast-target/', view.BroadcastTargetView.as_view()),
    path('broadcast/', view.BroadcastView.as_view()),
    

]
