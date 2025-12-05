from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from .views import UserDetailView, LogoutView

app_name = 'user'

urlpatterns = [
    path('me/', UserDetailView.as_view(), name='user_detail'),
]
