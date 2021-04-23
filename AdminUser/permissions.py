from rest_framework.permissions import BasePermission
from .models import AdminProfile

#Maybe subclass isAuthenticated?
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        try:
            profile = AdminProfile.objects.get(user=request.user)
            request.profile = profile
            return True
        except:
            return False