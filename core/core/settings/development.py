from datetime import timedelta
from .base import *

DEBUG = True

SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
})

ALLOWED_HOSTS.append("127.0.0.1")





