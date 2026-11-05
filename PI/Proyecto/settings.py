"""
Django settings for PI project (PetShop — Proyecto Integrado).

CORREGIDO respecto al original:
  1. INSTALLED_APPS: 'tienda' -> 'tiendaApp' (el nombre real de la app) y
     webpay se registra directo (su AppConfig es opcional).
  2. ROOT_URLCONF / WSGI_APPLICATION: 'PI.*' -> 'Proyecto.*' (la carpeta
     real del proyecto; manage.py y wsgi.py también se corregieron).
  3. TIME_ZONE: UTC -> 'America/Santiago' (proyecto chileno).
  4. RNF-05: cierre de sesión por inactividad (SESSION_COOKIE_AGE).
  5. LOGIN_URL / LOGIN_REDIRECT_URL / LOGOUT_REDIRECT_URL: le dicen a Django
     a dónde mandar al usuario con/sin sesión (RF-07).
  6. EMAIL: 'MAILERS' no existe en Django; el setting correcto es
     EMAIL_BACKEND (consola mientras desarrollamos).
  7. Context processor del carrito (numerito en la barra de navegación).
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-bz0$w*2yf2+6m!46mg6yz)a-08#==l7rl^k83h%xnxn@6)v1hk'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Para probar WebPay en local con ngrok, agrega tu dominio *.ngrok-free.app
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.app', '.ngrok.io']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',   # |intcomma: precios CLP con separador de miles
    'tiendaApp',
    'webpay',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
                # Numerito del carrito en la barra de todas las páginas
                'tiendaApp.context_processors.carrito_cantidad',
            ],
        },
    },
]

WSGI_APPLICATION = 'Proyecto.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
import pymysql
pymysql.install_as_MySQLdb()
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'lopets2',
        'USER': 'root',
        'PASSWORD': 'inacap'
    }
}

# --- Para pasar a Supabase (PostgreSQL) cuando toque:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'postgres',
#         'PASSWORD': 'TU_CONTRASEÑA_SUPABASE',
#         'HOST': 'db.TU-PROYECTO.supabase.co',
#         'PORT': '5432',
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ------------------------------------------------------------- Autenticación
# CÓMO entra un usuario (RF-07). Django prueba estas clases en orden:
#   1. ModelBackend (estándar de Django): valida por username -> sirve para
#      el admin y los usuarios de demostración.
#   2. tiendaApp.backends.CorreoBackend (nuestro): si lo escrito parece un
#      correo, valida por email -> así entran los clientes sin username.
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'tiendaApp.backends.CorreoBackend',
]
# ------------------------------------------------------------- Acceso
# A dónde manda Django cuando una página pide login (@login_required)
LOGIN_URL = 'login'
# A dónde va el usuario después de iniciar sesión
LOGIN_REDIRECT_URL = 'tiendaApp:home'
# A dónde va después de cerrar sesión
LOGOUT_REDIRECT_URL = 'tiendaApp:home'

# RNF-05: cierre de sesión por inactividad (30 min en segundos).
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True  # el contador se reinicia con cada acción


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'es'

# Formato de números chileno (18.990): el locale 'es' genérico usa espacio,
# así que lo sobrescribimos con el módulo Proyecto/formats/es.py.
FORMAT_MODULE_PATH = 'Proyecto.formats'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
if os.path.isdir(STATIC_DIR):
    STATICFILES_DIRS = [STATIC_DIR]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Email: mientras desarrollamos los correos se IMPRIMEN en la consola del
# runserver (backend de consola). Ningún setting 'MAILERS' existe en Django.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
