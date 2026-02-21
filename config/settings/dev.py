from .base import *
import os

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Override SECRET_KEY for development
SECRET_KEY = 'dev-secret-key-change-in-production'

# Database — PostgreSQL (siempre)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'db_dev'),
        'USER': os.getenv('POSTGRES_USER', 'dev_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', '12345'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}


# CORS para desarrollo
CORS_ALLOW_ALL_ORIGINS = True


# Email backend para desarrollo (mostrar en consola)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging para desarrollo
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}