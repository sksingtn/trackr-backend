from rest_framework.permissions import BasePermission
from .models import FacultyProfile


class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        try:
            profile = FacultyProfile.objects.get(user=request.user)
            request.profile = profile
            return True
        except:
            return False
