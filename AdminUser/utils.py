from datetime import timedelta

from rest_framework.exceptions import ValidationError

from base.models import Batch
from StudentUser.models import StudentProfile
from FacultyUser.models import FacultyProfile

FACULTY_INVITE_MAX_AGE = timedelta(days=7)

class ApiErrors:
    #Centralised error messages , to be used in tests too.
    START_TIME_GREATER = 'start time cant be greater than end time!'
    NO_OWNERSHIP = 'The requested {resource} was not {action} by current admin!'
    SLOT_OVERLAP = 'Requested timing overlaps with {title} ({start_time} - {end_time})'
    FACULTY_SLOT_OVERLAP = '{faculty} already has a class in {batch} at ({start_time} - {end_time})'

class BatchMixin:
    def get_batch(self, batch_id):
        try:
            batch = self.request.profile.batch_set.get(pk=batch_id)
            return batch
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist!')

class StudentBatchMixin:

    def get_batch(self, batch_id):
        try:
            batch = self.request.profile.batch_set.get(pk=batch_id)
            return batch
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist!')

    def get_student_queryset(self, batch_id, student_list):
        source_batch = self.get_batch(batch_id)
        students = StudentProfile.objects.filter(batch=source_batch)
        if not students:
            raise ValidationError('Source batch is already empty!')

        if student_list:
            students = students.filter(pk__in=student_list)
            if students.count() != len(student_list):
                raise ValidationError(
                    'Invalid student IDs or they dont belong to the source batch!')

        return source_batch, students


class FacultyMixin:
    def get_faculty(self, faculty_id):
        try:
            faculty = FacultyProfile.objects.get(pk=faculty_id, admin=self.request.profile)
            return faculty
        except FacultyProfile.DoesNotExist:
            raise ValidationError('Matching Faculty does not exist!')



