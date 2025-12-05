import os
from .env import get_env_setting

# Определяем, какие настройки использовать
DJANGO_ENV = get_env_setting('DJANGO_ENV', 'local')

if DJANGO_ENV == 'production':
    from .production import *
else:
    from .local import *

# Устанавливаем SECRET_KEY из env
SECRET_KEY = get_env_setting('SECRET_KEY', SECRET_KEY)
