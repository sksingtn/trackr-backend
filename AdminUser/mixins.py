from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from base.models import Batch
from StudentUser.models import StudentProfile
from FacultyUser.models import FacultyProfile

#TODO: add caching to some mixins
class GetBatchMixin:
    def get_batch(self, batch_id):
        try:
            return self.request.profile.batch_set.get(uuid=batch_id)
        except Batch.DoesNotExist:
            raise ValidationError('Matching batch does not exist!')


class GetFacultyMixin:
    def get_faculty(self, faculty_id):
        try:
            return self.request.profile.connected_faculties.get(uuid=faculty_id)
        except FacultyProfile.DoesNotExist:
            raise ValidationError('Matching Faculty does not exist!')


class BatchToggleMixin:
    def put(self, request):
        action = self.action
        keyword = 'resumed' if action else 'paused'

        allBatches = request.profile.batch_set.filter(active=not action)
        found = allBatches.count()

        if found == 0:
            return Response(
                {'status': 1, 'data': f'All Batches are already {keyword}!'}, status=status.HTTP_200_OK)

        allBatches.update(active=action)

        return Response({'status': 1, 'data': f'{found} batches {keyword}!'}, status=status.HTTP_200_OK)


class GetStudentMixin:

    def get_student_queryset(self, source_batch, student_list):
        students = StudentProfile.objects.filter(batch=source_batch)
        if not students:
            raise ValidationError('Source batch is already empty!')

        if student_list:
            students = students.filter(uuid__in=student_list)
            if students.count() != len(student_list):
                raise ValidationError(
                    'Invalid student IDs or they dont belong in the source batch!')

        return  students