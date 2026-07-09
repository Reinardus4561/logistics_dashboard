from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-logistics-dashboard-secret-key')

# Detect if running on Render
IS_RENDER = os.environ.get('RENDER', 'False').lower() in ['true', '1', 'yes']

# DEBUG: False in production (Render) by default, True in development
DEBUG = os.environ.get('DEBUG', str(not IS_RENDER)).lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS configuration
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

ENV_ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS')
if ENV_ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend([host.strip() for host in ENV_ALLOWED_HOSTS.split(',')])

# Support fallback wildcard if not on production
if not IS_RENDER:
    ALLOWED_HOSTS.append('*')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise Middleware for serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'logistics_dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'logistics_dashboard.wsgi.application'

# DATABASE CONFIGURATION
# Render uses SQLite; Localhost can use MySQL (default) or SQLite if configured via env
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite' if IS_RENDER else 'mysql')

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'logistics_db'),
            'USER': os.environ.get('DB_USER', 'Rein14'),
            'PASSWORD': os.environ.get('DB_PASSWORD', '456179'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'dashboard', 'static'),
]

# WhiteNoise storage configuration for compression and caching (Django 4.2+)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
