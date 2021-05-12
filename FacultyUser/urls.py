from django.urls import path, re_path
from . import views as view
from rest_framework.authtoken import views

urlpatterns = [
    path('signup/', view.CreateAccountView.as_view()),
    path('timeline/', view.TimelineView.as_view()),

    path('batch/', view.BatchView.as_view()),
    path('broadcast/', view.BroadcastView.as_view()),
    path('broadcast/<int:batch_id>/', view.BroadcastView.as_view())

]
