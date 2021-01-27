from django.urls import path,re_path
from django.contrib import admin
import api.views as view
from rest_framework.authtoken import views

urlpatterns = [
    #Admin Login/Signup APIs
    path('admin-signup/', view.SignupView.as_view()),
    path('admin-login/',views.obtain_auth_token),

    #Admin Faculty Handling
    path('admin-faculty/',view.FacultyView.as_view()),

    #Admin Slot Handling
    path('admin-slots/',view.SlotView.as_view()),
    path('admin-slots/<int:slot_id>/', view.SlotView.as_view()),

    #Admin Batch Handling
    path('admin-batch/', view.BatchView.as_view()),
    path('admin-batch/<int:batch_id>/',view.BatchView.as_view()),
    

]
