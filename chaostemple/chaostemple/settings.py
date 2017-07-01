"""
Django settings for chaostemple project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
from dateutils import relativedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SITE_ID = 1


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/


# Application definition

INSTALLED_APPS = (
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'registration',

    'core',
    'dossier',
    'althingi',
    'jsonizer',
)

# django_registration_redux settings
ACCOUNT_ACTIVATION_DAYS = 1
REGISTRATION_AUTO_LOGIN = True
REGISTRATION_OPEN = False

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'core.middleware.AccessMiddleware',
    'core.middleware.ExtraVarsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',

                'core.contextprocessors.globals',
            ],
        },
    },
]

ROOT_URLCONF = 'chaostemple.urls'

WSGI_APPLICATION = 'chaostemple.wsgi.application'

LANGUAGES = (
    ('is', 'Icelandic'),
)

LOCALE_PATHS = (
    'locale',
)


# Various project settings
MEANING_OF_RECENT = relativedelta(months=1)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

LOGIN_REDIRECT_URL = '/'

from chaostemple.local_settings import *
if DEBUG:
    import imp
    try:
        imp.find_module('debug_toolbar')

        INSTALLED_APPS += ('debug_toolbar.apps.DebugToolbarConfig',)
        MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
        DEBUG_TOOLBAR_CONFIG = {
            'JQUERY_URL': ''
        }
    except ImportError:
        # Silently continue if django-debug-toolbar isn't installed
        pass

from chaostemple.constants import *
