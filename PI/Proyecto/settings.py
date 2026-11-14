import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
ON_VERCEL = bool(os.getenv('VERCEL'))

TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# --- SECRET_KEY ---
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if ON_VERCEL and not SECRET_KEY:
    raise RuntimeError('Falta DJANGO_SECRET_KEY en las variables de entorno de Vercel')
SECRET_KEY = SECRET_KEY or 'django-insecure-bz0$w*2yf2+6m!46mg6yz)a-08#==l7rl^k83h%xnxn@6)v1hk'

# --- DEBUG ---
DEBUG = os.getenv('DJANGO_DEBUG', 'False' if ON_VERCEL else 'True').lower() == 'true'
if ON_VERCEL:
    DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.app', '.ngrok.io', '.vercel.app']

# --- CSRF y proxy HTTPS para Vercel ---
CSRF_TRUSTED_ORIGINS = ['https://*.vercel.app']
if ON_VERCEL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'tiendaApp',
    'webpay',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Para servir estáticos en Vercel
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Proyecto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tiendaApp.context_processors.carrito_cantidad',
            ],
        },
    },
]

WSGI_APPLICATION = 'Proyecto.wsgi.application'


# --- DB Supabase ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres.gbbcyqhspbsypukfugfz',
        'PASSWORD': 'LopetsEVA03',
        'HOST': 'aws-1-sa-east-1.pooler.supabase.com',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'prepare_threshold': None,
        },
        'CONN_MAX_AGE': 0,
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'tiendaApp.backends.CorreoBackend',
]
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'tiendaApp:home'
LOGOUT_REDIRECT_URL = 'tiendaApp:home'

SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True

LANGUAGE_CODE = 'es'
FORMAT_MODULE_PATH = 'Proyecto.formats'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
if os.path.isdir(STATIC_DIR):
    STATICFILES_DIRS = [STATIC_DIR]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --- CONFIGURACIÓN DE SUPABASE STORAGE (DE TU COMPAÑERO) ---
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
SUPABASE_STORAGE_KEY = os.environ.get('SUPABASE_STORAGE_KEY', '').strip()
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'lopets-imagenes')

STORAGES = {
    'default': {'BACKEND': 'tiendaApp.almacenamiento.AlmacenamientoImagenes'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}, # Usamos whitenoise aquí para Vercel
}