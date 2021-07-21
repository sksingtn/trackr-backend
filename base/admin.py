from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
from .models import Batch,Slot,Timing,CustomUser,Activity


admin.site.register([ Batch,Slot, Timing ,Activity,CustomUser])
