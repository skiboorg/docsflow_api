REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     'rest_framework.permissions.IsAuthenticated',
    # ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],

    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

DJOSER = {
    'USER_ID_FIELD': 'uuid',
    'LOGIN_FIELD': 'email',
    'USER_CREATE_PASSWORD_RETYPE': True,
    'SET_USERNAME_RETYPE': True,
    'SET_PASSWORD_RETYPE': True,
    'SEND_ACTIVATION_EMAIL': False,
    'SERIALIZERS': {
        'user_create': 'apps.user.serializers.UserCreateSerializer',
        'user': 'apps.user.serializers.UserSerializer',
        'current_user': 'apps.user.serializers.UserSerializer',
        'token_create': 'apps.user.serializers.CustomTokenCreateSerializer',
    },
    'PERMISSIONS': {
        'user': ['rest_framework.permissions.IsAuthenticated'],
        'user_list': ['rest_framework.permissions.IsAdminUser'],
    }
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
