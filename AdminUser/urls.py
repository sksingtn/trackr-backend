from django.urls import path,re_path
from django.contrib import admin
from . import views as view
from rest_framework.authtoken import views

urlpatterns = [
    #Admin Login/Signup APIs
    path('signup/', view.SignupView.as_view(),name='admin-signup'),
    #This should be a common endpoint and return the type of user.
    path('login/',views.obtain_auth_token), 
    #A /logout endpoint is also needed to refresh the token

    #Admin Faculty Handling
    path('faculty/',view.FacultyView.as_view(),name='admin-faculty'),

    #Admin Slot Handling
    path('slots/',view.SlotView.as_view(),name="admin-slots"),
    path('slots/<int:slot_id>/', view.SlotView.as_view(),name="admin-slots"),

    #Admin Batch Handling
    path('batch/', view.BatchView.as_view()),
    path('batch/<int:batch_id>/',view.BatchView.as_view()),

    #Admin resume/pause batches
    path('active-toggle/',view.ToggleView.as_view(),name="admin-active-toggle"),
    path('batch-toggle/<int:batch_id>/',view.ToggleView.as_view(),name="admin-batch-toggle"),

    #Admin Student Handling
    

]
