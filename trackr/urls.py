from django.contrib import admin
from django.urls import path,re_path,include
from django.conf.urls.static import static
from django.conf import settings
import debug_toolbar


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/admin-',include('AdminUser.urls')),
    path('api/faculty-', include('FacultyUser.urls')),
    path('api/student-', include('StudentUser.urls')),
    #path('api/', include('base.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
