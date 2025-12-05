from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API routes
    path('api/', include('apps.api.urls', namespace='api')),
    
    # Djoser auth endpoints
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    
    # REST Framework auth endpoints (for browsable API)
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
