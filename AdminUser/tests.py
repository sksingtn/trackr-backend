from datetime import time
from json import loads

from django.test import TransactionTestCase
from django.urls import reverse

from rest_framework.test import APIRequestFactory,force_authenticate,APIClient
from rest_framework.authtoken.models import Token

from . import views as AdminView
from .models import AdminProfile
from FacultyUser.models import FacultyProfile
from base.models import Batch,Slot
from base import response as ApiResponse


class AdminSignupInvite(TransactionTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
    
    def test_admin_signup_and_invite(self):
        """
        Testing for successful creation of admin profile
        and token after signup.
        """
        url = reverse('admin-signup')
        postData = {'email':'admin@test.com','password':'password',
                    'name':'admin','timezone':'Asia/Kolkata'}

        request = self.factory.post(url,postData,content='json')
        response = AdminView.SignupView.as_view()(request)
        self.assertEqual(response.status_code,201)
        
        adminInstance = AdminProfile.objects.get(name=postData['name'])
        self.assertEqual(adminInstance.user.email,postData['email'])
        self.assertEqual(Token.objects.count(),1)

        url = reverse('admin-faculty')

        """
        Testing invite functionailty when email is provided.
        """
        postData = {'name':'faculty1','email':'faculty@test.com'}
        request = self.factory.post(url,postData)
        force_authenticate(request,user=adminInstance.user)       
        response = AdminView.FacultyView.as_view()(request)
        self.assertEqual(response.status_code,201)
        facultyInstance = FacultyProfile.objects.get(name=postData['name'])
        self.assertEqual(facultyInstance.status,'INVITED')
        self.assertEqual(facultyInstance.admin,adminInstance)
        self.assertIsNotNone(facultyInstance.user,'user is not created on invite')
        self.assertEqual(facultyInstance.user.email,postData['email'])

        """
        Testing invite functionailty when email is not provided.
        """

        postData = {'name':'faculty2'}
        request = self.factory.post(url,postData)
        force_authenticate(request,user=adminInstance.user)        
        response = AdminView.FacultyView.as_view()(request)
        self.assertEqual(response.status_code,201)
        facultyInstance = FacultyProfile.objects.get(name=postData['name'])
        self.assertEqual(facultyInstance.status,'UNVERIFIED')
        self.assertEqual(facultyInstance.admin,adminInstance)
        self.assertIsNone(facultyInstance.user,'user should not be created on empty email')


        self.assertEqual(FacultyProfile.objects.all().count(),2)



class AdminSlotHandling(TransactionTestCase):
    
    #Clarify about testcase design
    def setUp(self):
        adminPostData = {'email':'admin1@test.com','password':'password',
                        'name':'admin1','timezone':'Asia/Kolkata'}
        client = APIClient()
        resp = client.post(reverse('admin-signup'),adminPostData)
        self.mainAdmin = AdminProfile.objects.get(name=adminPostData['name'])       
        self.mainBatch = Batch.objects.create(title="admin1_batch",admin=self.mainAdmin)
        self.mainFaculty = FacultyProfile.objects.create(name="admin1_faculty",admin=self.mainAdmin)
        self.mainSlot = Slot.create_slot(batch=self.mainBatch,faculty=self.mainFaculty,title='admin1_slot1'
                                ,start_time=time(hour=8),end_time=time(hour=9),weekday=0)


        #Creating another admin and its descendants.
        client.post(reverse('admin-signup'),{'password':'password','email':'admin2@gmail.com','name':'admin2',
                                            'timezone':'Asia/Kolkata'})
        self.otherAdmin = AdminProfile.objects.get(name='admin2')
       
        self.factory = APIRequestFactory()
        
   
    def create_request_object(self,data,method="post",view=AdminView.SlotView,**kwargs):
        url = reverse('admin-slots',kwargs=kwargs)
        factory = APIRequestFactory()
        request = getattr(factory,method)(url,data,format='json')
        force_authenticate(request,user=self.mainAdmin.user)
        response = view.as_view()(request,**kwargs)
        status_code = response.status_code
        response.render()

        return status_code,loads(response.content)

    
    def test_startTime_endTime(self):
        """
        Slot can't be created if start time is greater than end time.
        """
        postData = { 'title':'admin1_slot2','batch':self.mainBatch.uuid,'faculty':self.mainFaculty.uuid,
                    'start_time':'20:00','end_time':'18:00','weekday':1}
        status_code,response = self.create_request_object(postData)        
        self.assertEqual(status_code,400)
        self.assertEqual(response.get('status'),0)
        self.assertEqual(response.get('data'),ApiResponse.startTimeGreaterResponse())
        self.assertEqual(Slot.objects.all().count(),1)


    def test_time_span(self):
        """
        Slot can't be created if time interval crosses into next day.
        """
        postData = {'title':'admin1_slot2','batch':self.mainBatch.uuid,'faculty':self.mainFaculty.uuid,
                    'start_time':'20:00','end_time':'02:00','weekday':1}
        status_code,response = self.create_request_object(postData)        
        self.assertEqual(status_code,400)
        self.assertEqual(response.get('status'),0)
        self.assertEqual(response.get('data'),ApiResponse.startTimeGreaterResponse())
        self.assertEqual(Slot.objects.all().count(),1)

   
    def test_faculty_does_not_belong(self):
        """
        Slot cant be created if admin tries to create a slot with a faculty
        that was not invited by that admin.
        """

        #Create a new faculty object that was not invited by main admin.
        otherFaculty = FacultyProfile.objects.create(name="admin2_faculty",admin=self.otherAdmin)

        postData = {'title':'admin1_slot2','batch':self.mainBatch.uuid,'faculty':otherFaculty.uuid,
                    'start_time':'20:00','end_time':'21:00','weekday':1}
        status_code,response = self.create_request_object(postData)        
        self.assertEqual(status_code,400)
        self.assertEqual(response.get('status'),0)
        self.assertEqual(response.get('data'),ApiResponse.noFacultyOwnershipResponse())
        self.assertEqual(Slot.objects.all().count(),1)


    def test_batch_does_not_belong(self):
        """
        Slot cant be created if admin tries to create a slot with a batch
        that was not created by that admin.
        """

        #Create a new batch object that was not invited by main admin.
        otherBatch = Batch.objects.create(title="admin2_batch",admin=self.otherAdmin)

        postData = {'title':'admin1_slot2','batch':otherBatch.uuid,'faculty':self.mainFaculty.uuid,
                    'start_time':'20:00','end_time':'21:00','weekday':1}
        status_code,response = self.create_request_object(postData)        
        self.assertEqual(status_code,400)
        self.assertEqual(response.get('status'),0)
        self.assertEqual(response.get('data'),ApiResponse.noBatchOwnershipResponse())
        self.assertEqual(Slot.objects.all().count(),1)


    def test_slot_overlap(self):
        """
        Consider a Slot with weekday = Monday ,faculty = John ,timing 8-9 PM,batch 1st
        The above slot cant be created in two overlapping scenarios :
        1- If a slot exist in batch 1st on Monday between 8-9 PM.
        2- If a slot exist in other batches where John taught on Monday between 8-9 PM.
        Note- Adjacent slots are allowed.
        """
        
        #1st Interation tests for presence of 1st scenario and so on

        newBatch = Batch.objects.create(title="admin1_batch2",admin=self.mainAdmin)
        for iteration,batch in enumerate((self.mainBatch,newBatch),start=1):

            #All possible pattern of intervals that overlap with 08:00 - 09:00.
            for start_time,end_time in (('07:30','08:15'),('07:30','09:00'),('07:30','09:15'),
                                        ('08:00','08:15'),('08:00','09:00'),('08:00','09:15'),
                                        ('08:15','08:45'),('08:15','09:00'),('08:15','09:15')): 

                postData = {'title':'admin1_slot2','batch':batch.uuid,'faculty':self.mainFaculty.uuid,
                            'weekday':0,'start_time':start_time,'end_time':end_time}

                status_code,response = self.create_request_object(postData)

                self.assertEqual(status_code,400,end_time)
                self.assertEqual(response.get("status"),0)

                if iteration == 1:
                    self.assertEqual(response.get('data'),ApiResponse.overlappedSlotResponse(title=self.mainSlot.title,
                                        startTime=self.mainSlot.get_start_time(),endTime=self.mainSlot.get_end_time()))

                elif iteration == 2:
                    self.assertEqual(response.get('data'),ApiResponse.overlappedFacultyResponse(facultyName=self.mainFaculty.name,
                                        batchName=self.mainBatch.title,startTime=self.mainSlot.get_start_time(),
                                        endTime=self.mainSlot.get_end_time()))
       

        self.assertEqual(Slot.objects.count(),1)

    #TODO: Need a non overlapping test case.

    def test_overlap_on_moving(self):
        """
        Slot can't be updated if its moved into the 2 overlapping scenarios.
        1 - Overlaps with existing slots in current batch
        2 - OVerlaps with a parallel class in another batch taught by same faculty
        """

        newBatch = Batch.objects.create(title="admin1_batch2",admin=self.mainAdmin)
        newFaculty = FacultyProfile.objects.create(name="admin1_faculty2",admin=self.mainAdmin)

        #1st Interation tests for presence of 1st scenario and so on.
        for index,(batch,faculty) in enumerate(((self.mainBatch,newFaculty),(newBatch,self.mainFaculty)),start=2):

            testSlot = Slot.create_slot(batch=batch,faculty=faculty,title=f'admin1_slot{index}'
                                    ,start_time='20:00',end_time='21:00',weekday=0)

            self.assertEqual(Slot.objects.all().count(),index)

            postData = {'faculty':faculty.uuid,'title':'admin1_slot2_moved',
                        'start_time':'08:30','end_time':'09:30','weekday':0}
            status_code,response = self.create_request_object(postData,method="put",view=AdminView.SlotRUDView
                                                                ,slot_id=testSlot.uuid) 

            self.assertEqual(status_code,400)
            self.assertEqual(response.get('status'),0)   
            
    
    def  test_slot_overlap_when_updating(self):
        """
        When updating a slot's timing , an overlap should not be detected
        between current timing and requested timing, for ex: 08:00-09:00 to 08:30-09:30 
        """

        postData = {'title':'admin1_slot2','faculty':self.mainFaculty.uuid,
                    'weekday':0,'start_time':'08:30','end_time':'09:30'}

        status_code,response = self.create_request_object(postData,method="put",view=AdminView.SlotRUDView,
                                                            slot_id=self.mainSlot.uuid) 
        updatedSlot = Slot.objects.get(pk=self.mainSlot.pk)
        self.assertEqual(status_code,200)
        self.assertEqual(response.get('status'),1)
        self.assertEqual((updatedSlot.start_time,updatedSlot.end_time,updatedSlot.weekday),
                         (time(hour=8,minute=30),time(hour=9,minute=30),0),'Incorrect values after update')  
        self.assertEqual(Slot.objects.all().count(),1)


    def test_slot_update_ok(self):      
        """
        Test slot update by changing every attribute except batch during slot update.
        """

        newFaculty = FacultyProfile.objects.create(name="admin1_faculty2",admin=self.mainAdmin)
        postData = {'faculty':newFaculty.uuid,'title':'admin1_slot_name_changed',
                    'start_time':'20:00','end_time':'21:00','weekday':1}


        #Should not clash with classes on same time but different weekdays.
        Slot.create_slot(batch=self.mainBatch,faculty=self.mainFaculty,title='admin1_slot2',
                            start_time=time(hour=20),end_time=time(hour=21),weekday=2)


        status_code,response = self.create_request_object(postData,method="put",view=AdminView.SlotRUDView,
                                                            slot_id=self.mainSlot.uuid)        
        updatedSlot = Slot.objects.get(pk=self.mainSlot.pk)


        self.assertEqual(status_code,200)
        self.assertIsNotNone(response.get('data'))
        self.assertEqual(Slot.objects.all().count(),2)  
        self.assertEqual((updatedSlot.start_time,updatedSlot.end_time,updatedSlot.weekday),
                         (time(hour=20),time(hour=21),1),'Incorrect values after update')   
        self.assertEqual(updatedSlot.faculty,newFaculty)
        self.assertEqual(updatedSlot.title,'admin1_slot_name_changed')
        
        

    def test_slot_create_ok(self):
        """
        Test of simple slot creation.
        """

        #Should not clash with classes on same time but different weekdays.
        Slot.create_slot(batch=self.mainBatch,faculty=self.mainFaculty,title='admin1_slot2',
                                start_time=time(hour=20),end_time=time(hour=21),weekday=1)

        postData = {'faculty':self.mainFaculty.uuid,'batch':self.mainBatch.uuid,'title':'admin1_slot2',
                    'start_time':'20:00','end_time':'21:00','weekday':0}

        status_code,response = self.create_request_object(postData) 


        self.assertEqual(status_code,201)
        self.assertIsNotNone(response.get('data'))
        self.assertEqual(Slot.objects.all().count(),3)

        
