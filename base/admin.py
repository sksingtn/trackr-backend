from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
from .models import Batch,Slot,Timing,CustomUser,Activity


@admin.register(CustomUser)
class UserAdmin(UserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

#For Importing all the model classes from models.py
"""imported_models = [item for item in map(lambda x: getattr(all_models, x), dir(all_models)) if inspect.isclass(
    item) and issubclass(item, django.db.models.Model) and not issubclass(item, django.contrib.auth.models.AbstractUser)]"""


admin.site.register([ Batch,Slot, Timing ,Activity])
