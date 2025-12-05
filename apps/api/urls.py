from django.urls import path, include

app_name = 'api'

urlpatterns = [
    path('document/', include('apps.document.urls')),
    path('company/', include('apps.company.urls')),
    path('shared/', include('apps.shared.urls')),
    path('auth/', include('apps.user.urls')),
]
