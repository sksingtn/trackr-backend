from rest_framework.permissions import BasePermission
from .models import StudentProfile


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        try:
            profile = StudentProfile.objects.get(user=request.user)
            request.profile = profile
            return True
        except:
            return False
