from django.contrib import admin
from .models import Batch,Slot,CustomUser,Activity


admin.site.register([ Batch,Slot,Activity,CustomUser])
