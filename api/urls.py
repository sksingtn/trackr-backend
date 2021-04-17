from django.urls import path,re_path
from django.contrib import admin
import api.views as view
from rest_framework.authtoken import views

urlpatterns = [
    #Admin Login/Signup APIs
    path('admin-signup/', view.SignupView.as_view(),name='admin-signup'),
    #This should be a common endpoint and return the type of user.
    path('admin-login/',views.obtain_auth_token), 
    #A /logout endpoint is also needed to refresh the token

    #Admin Faculty Handling
    path('admin-faculty/',view.FacultyView.as_view(),name='admin-faculty'),

    #Admin Slot Handling
    path('admin-slots/',view.SlotView.as_view(),name="admin-slots"),
    path('admin-slots/<int:slot_id>/', view.SlotView.as_view(),name="admin-slots"),

    #Admin Batch Handling
    path('admin-batch/', view.BatchView.as_view()),
    path('admin-batch/<int:batch_id>/',view.BatchView.as_view()),
    

]
