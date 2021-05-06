from django.urls import path, re_path
from . import views as view
from rest_framework.authtoken import views

urlpatterns = [
    path('create-account/', view.CreateAccountView.as_view()),
    path('timeline/', view.TimelineView.as_view()),

]
