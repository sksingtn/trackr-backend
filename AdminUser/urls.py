from django.urls import path

from . import views as view

urlpatterns = [

    path('signup/', view.SignupView.as_view(),name='admin-signup'),
    
    ##Admin Faculty Handling

    #Shows a paginated list of all faculties under admin with search functionality on GET.
    path('faculty/',view.FacultyView.as_view(),name='admin-faculty'),
    path('faculty-delete/<uuid:faculty_id>',view.FacultyDeleteView.as_view(), name='admin-faculty-delete'), 
    #Add/override email of a Unverified/Invited faculty on POST.
    path('faculty-invite/<uuid:faculty_id>',view.FacultyInviteView.as_view(), name='admin-faculty-invite'),
    #Resends the invitation link to a Invited user on POST.
    path('faculty-resend-invite/<uuid:faculty_id>',view.FacultyReInviteView.as_view(),
                     name='admin-faculty-resend-invite'),
    path('faculty-stats',view.FacultyStatsView.as_view(),name='faculty-stats'),
    
    ##Admin Slot Handling

    #TODO: Need a retrieve method
    #Create a new slot on POST.
    path('slots/',view.SlotView.as_view(),name="admin-slots"),
    #Update/Delete the given slot on PUT/DELETE.
    path('slots/<int:slot_id>/', view.SlotView.as_view(),name="admin-slots"),
 
    ###Admin Batch Handling
   
    path('batch/', view.BatchListCreateView.as_view(), name="admin-batch"), 
    path('batch-detail/', view.BatchDetailedListView.as_view(),name="admin-batch-detailed-list"),
    path('batch/<uuid:batch_id>/',view.BatchDetailUpdateView.as_view(), name="admin-batch-detail-update"),
    path('batch-delete/<uuid:batch_id>/',view.BatchDeleteView.as_view(), name="admin-batch-delete"),
    path('batch-active-toggle/<uuid:batch_id>/',view.BatchToggleView.as_view(), name="admin-batch-toggle"),
    path('batch-pause-all/',view.BatchPauseAllView.as_view(),name="admin-batch-pause"),
    path('batch-resume-all/', view.BatchResumeAllView.as_view(),name="admin-batch-resume"),

    ###Admin Student Handling
    path('list-students/<uuid:batch_id>/',view.StudentListView.as_view(),name='admin-list-students'),
    path('move-students/<uuid:source_batch_id>/<uuid:destination_batch_id>/',
                                            view.StudentMoveView.as_view(),name='admin-move-students'),    
    path('delete-students/<uuid:batch_id>/',view.StudentDeleteView.as_view(),name='admin-delete-students'),

    ### Broadcast Messages to Student/Faculty
    path('broadcast-target/', view.BroadcastTargetView.as_view(),
         name="admin-broadcast-target"),
    path('broadcast/', view.BroadcastView.as_view(), name="admin-broadcast"),


]
