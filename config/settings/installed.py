INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_cleanup',
    'django_filters',
    'djoser',
    
    # Local apps
    'apps.document',
    'apps.company',
    'apps.api',
    'apps.common',
    'apps.user',
    'apps.shared',
]
