

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

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tiendaApp',                
    'webpay.apps.WebpayConfig'  
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
                'tiendaApp.context_processors.carrito_cantidad',
            ],
        },
    },
]

WSGI_APPLICATION = 'Proyecto.wsgi.application'   


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
#
# ESTRATEGIA (documentada en el README): SQLite para desarrollar el sprint
# actual; al cerrar el modelo de datos, se cambia al bloque Supabase de más
# abajo (requiere: pip install "psycopg[binary]").

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'lopets',
        'USER': 'root',
        'PASSWORD': 'inacap'
    }
}

# ---- SUPABASE (PostgreSQL) -----------------------------------------------
# Descomenta este bloque y COMENTA el de sqlite de arriba cuando toque migrar.
# Los datos salen de Supabase: Project Settings -> Database -> Connection
# string (usa la contraseña de la BD, NO la del panel).
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'postgres',
#         'PASSWORD': 'TU_PASSWORD_DE_SUPABASE',
#         'HOST': 'db.TUPROYECTO.supabase.co',
#         'PORT': '5432',
#         'CONN_MAX_AGE': 60,                     # reutiliza conexiones
#         'OPTIONS': {'sslmode': 'require'},      # Supabase exige SSL
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


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Santiago'    # <- CORREGIDO (era UTC): proyecto chileno

USE_I18N = True

USE_TZ = True


# Sesión — RNF-05: "cierre de sesión automático tras 15 minutos de
# inactividad". SESSION_SAVE_EVERY_REQUEST hace que la cookie se renueve en
# cada interacción => los 15 min cuentan desde la ÚLTIMA acción (si no,
# contarían desde el login aunque el usuario estuviera activo).
# TIP: coméntalas mientras desarrollas para no perder la sesión a cada rato.
SESSION_COOKIE_AGE = 15 * 60          # 900 segundos
SESSION_SAVE_EVERY_REQUEST = True


# Autenticación (RF-07): dónde enviar al usuario sin sesión y a dónde
# devolverlo tras iniciar sesión / cerrar sesión.
LOGIN_URL = '/cuenta/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [STATIC_DIR]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Imágenes de productos (RF-01) — como en el taller: admin sube la imagen,
# queda guardada en media/productos/ y las plantillas la muestran.
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Email — CORREGIDO: el setting de Django es EMAIL_BACKEND (no 'MAILERS').
# Con 'console' los correos se imprimen en la consola de runserver (dev).
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
