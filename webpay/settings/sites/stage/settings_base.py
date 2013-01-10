"""private_base will be populated from puppet and placed in this directory"""
import logging.handlers
import dj_database_url
import private_base as private

from .. import splitstrip


DATABASES = {}
DATABASES['default'] = dj_database_url.parse(private.DATABASES_DEFAULT_URL)
DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
DATABASES['default']['OPTIONS'] = {'init_command': 'SET storage_engine=InnoDB'}


DATABASES['slave'] = dj_database_url.parse(private.DATABASES_SLAVE_URL)
DATABASES['slave']['ENGINE'] = 'django.db.backends.mysql'
DATABASES['slave']['OPTIONS'] = {'init_command': 'SET storage_engine=InnoDB'}

SLAVE_DATABASES = ['slave']

CACHE_PREFIX = private.CACHE_PREFIX

CACHES = {
    'default': {
        'BACKEND': 'caching.backends.memcached.CacheClass',
        'LOCATION': splitstrip(private.CACHES_DEFAULT_LOCATION),
        'TIMEOUT': 500,
        'KEY_PREFIX': CACHE_PREFIX,
    },
}

ADMINS = ()
MANAGERS = ADMINS

DEBUG = TEMPLATE_DEBUG = False

DEV = False

SITE_URL = 'https://marketplace.allizom.org'
MARKETPLACE_URL = SITE_URL

HMAC_KEYS = private.HMAC_KEYS

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(base.BASE_PASSWORD_HASHERS, HMAC_KEYS)

SECRET_KEY = private.SECRET_KEY

ENGAGE_ROBOTS = False

## Celery
BROKER_URL = private.BROKER_URL
CELERY_IGNORE_RESULT = True
CELERY_DISABLE_RATE_LIMITS = True
CELERYD_PREFETCH_MULTIPLIER = 1

## Log settings

SYSLOG_TAG = private.SYSLOG_TAG
#LOGGING = dict(loggers=dict(playdoh = {'level': logging.DEBUG}))

# HTTPS to disable HTTPS-only cookies.
SESSION_COOKIE_SECURE = True

#VERBOSE_LOGGING=True

DOMAIN = 'marketplace.allizom.org'
ISSUER = DOMAIN
NOTIFY_ISSUER = DOMAIN
VERBOSE_LOGGING = True
INAPP_REQUIRE_HTTPS = False

KEY = private.KEY
SECRET = private.SECRET

SOLITUDE_URL = 'https://payments.allizom.org'

SENTRY_DSN = private.SENTRY_DSN
