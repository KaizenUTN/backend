from .base import *
import os

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Override SECRET_KEY for development
SECRET_KEY = 'dev-secret-key-change-in-production'

# Database configuration for development
# Usa PostgreSQL si está disponible (Docker), sino SQLite
USE_POSTGRES = os.getenv('USE_POSTGRES', 'False') == 'True'

if USE_POSTGRES:
    # PostgreSQL para desarrollo con Docker
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
else:
    # SQLite para desarrollo local sin Docker (más rápido y simple)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'config' / 'db.sqlite3',
        }
    }

# CORS para desarrollo
try:
    import corsheaders
    INSTALLED_APPS = ['corsheaders'] + INSTALLED_APPS
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')
    CORS_ALLOW_ALL_ORIGINS = True
except ImportError:
    pass

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