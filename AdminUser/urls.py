from django.urls import path,re_path
from django.contrib import admin
from . import views as view
from rest_framework.authtoken import views

urlpatterns = [
    #Admin Login/Signup APIs
    path('signup/', view.SignupView.as_view(),name='admin-signup'),
    #This should be a common endpoint and return the type of user.
    path('login/',views.obtain_auth_token), 

    ##Admin Faculty Handling

    #Shows a paginated list of all faculties under admin with search functionality on GET.
    path('faculty/',view.FacultyView.as_view(),name='admin-faculty'),
    #Deletes the faculty on DELETE and provides a delete preview on GET.
    path('faculty-delete/<int:faculty_id>',view.FacultyDeleteView.as_view(), name='admin-faculty-delete'),
    #Add/override email of a Unverified/Invited faculty on POST.
    path('faculty-invite/<int:faculty_id>',view.FacultyInviteView.as_view(), name='admin-faculty-invite'),
    #Resends the invitation link to a Invited user on POST.
    path('faculty-resend-invite/<int:faculty_id>',view.FacultyReInviteView.as_view(), name='admin-faculty-resend-invite'),
    
    ##Admin Slot Handling

    #Create a new slot on POST.
    path('slots/',view.SlotView.as_view(),name="admin-slots"),
    #Update/Delete the given slot on PUT/DELETE.
    path('slots/<int:slot_id>/', view.SlotView.as_view(),name="admin-slots"),
 
    ###Admin Batch Handling

    #Shows a non-paginated list of batches on GET and created a new batch on POST.
    path('batch/', view.BatchView.as_view(),name="admin-batch"),
    #Shows detail of a single batch along with all the slots defined in it.
    path('batch/<int:batch_id>/', view.BatchView.as_view(),name="admin-batch"),
    #Shows a detailed paginated list of all batches on GET with search functionality.
    path('batch-detail/', view.BatchDetailView.as_view(), name="admin-batch-detail"),
    #Used to edit some parameters of a batch on PUT.
    path('batch-edit/<int:batch_id>/',view.BatchEditView.as_view(), name="admin-batch-edit"),
    #Deletes batch on DELETE and provides a delete preview on GET.
    path('batch-delete/<int:batch_id>/',view.BatchDeleteView.as_view(), name="admin-batch-delete"),
    #Enable/Disable a batch.
    path('batch-toggle/<int:batch_id>/',view.ToggleView.as_view(),name="admin-batch-toggle"),
    #Pause All the batches under admin's account.
    path('active-toggle/',view.ToggleView.as_view(),name="admin-active-toggle"),
    
    ###Admin Student Handling

    #Shows a paginated list of students under a given batch with search functionality on GET.
    path('list-students/<int:batch_id>/',view.StudentListView.as_view(),name='admin-list-students'),
    #Moves all/some students from one batch to another on PUT.
    path('move-students/<int:source_batch_id>/<int:destination_batch_id>/',
                                            view.StudentMoveView.as_view(),name='admin-move-students'),    
    #Deletes all/some students from a given batch on PUT.
    path('delete-students/<int:batch_id>/',view.StudentDeleteView.as_view(),name='admin-delete-students'),



]
