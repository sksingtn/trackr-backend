from django.contrib import admin
from django.urls import path,re_path,include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/admin-',include('AdminUser.urls')),
    #re_path(r'^api/faculty\-.*',include('FacultyUser.urls')),
    #re_path(r'^api/student\-.*',include('StudentUser.urls'))
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
