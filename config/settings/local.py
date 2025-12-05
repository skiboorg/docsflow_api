from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

from .database_sqlite import *
from .installed import *
from .rest import *
from .logging import *

# Local development settings
import socket
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[:-1] + '1' for ip in ips] + ['127.0.0.1', '10.0.2.2']
