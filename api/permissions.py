from rest_framework.permissions import BasePermission
from base.models import AdminProfile

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        try:
            profile = AdminProfile.objects.get(user=request.user)
            request.profile = profile
            return True
        except:
            return False