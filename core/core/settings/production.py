from datetime import timedelta
from decouple import config
from .base import *


DEBUG = False

ACCESS_MINUTES = config("JWT_ACCESS_MINUTES", default=15, cast=int)
REFRESH_DAYS = config("JWT_REFRESH_DAYS", default=1, cast=int)

SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=ACCESS_MINUTES), 
    'REFRESH_TOKEN_LIFETIME': timedelta(days=REFRESH_DAYS),   
})