from .base import *

DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com', 'server-ip']

from .database_postgres import *
from .installed import *
from .rest import *
from .logging import *

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Update logging for production
LOGGING['handlers']['file'] = {
    'level': 'ERROR',
    'class': 'logging.FileHandler',
    'filename': BASE_DIR / 'django_errors.log',
    'formatter': 'verbose'
}
LOGGING['root']['handlers'] = ['file']
LOGGING['root']['level'] = 'ERROR'
