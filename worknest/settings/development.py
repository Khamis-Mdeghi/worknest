from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True
# Use local storage in development
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'