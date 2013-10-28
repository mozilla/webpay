"""private_base will be populated from puppet and placed in this directory"""
import logging.handlers
import dj_database_url
import private_base as private

from webpay.settings import base

from .. import splitstrip

DOMAIN = 'marketplace.allizom.org'
ALLOWED_HOSTS = [DOMAIN]

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
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': splitstrip(private.CACHES_DEFAULT_LOCATION),
        'TIMEOUT': 500,
        'KEY_PREFIX': CACHE_PREFIX,
    },
}

ADMINS = ()
MANAGERS = ADMINS

DEBUG = TEMPLATE_DEBUG = False

DEV = False

SITE_URL = 'https://' + DOMAIN
MARKETPLACE_URL = SITE_URL
MARKETPLACE_OAUTH = {'key': private.MARKETPLACE_OAUTH_KEY,
                     'secret': private.MARKETPLACE_OAUTH_SECRET}

STATIC_URL_DOMAIN = 'marketplace-cdn.allizom.org'
STATIC_URL = 'https://%s/' % STATIC_URL_DOMAIN
MEDIA_URL = STATIC_URL + 'mozpay/media/'

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

DOMAIN = 'marketplace.allizom.org'
ISSUER = DOMAIN
NOTIFY_ISSUER = DOMAIN

KEY = DOMAIN
# This must match private_mkt.APP_PURCHASE_SECRET in marketplace settings.
SECRET = private.SECRET

SOLITUDE_URL = 'https://payments.allizom.org'
SOLITUDE_OAUTH = {'key': private.SOLITUDE_OAUTH_KEY,
                  'secret': private.SOLITUDE_OAUTH_SECRET}

SENTRY_DSN = private.SENTRY_DSN

# Hook into the production web flow.
BANGO_BASE_URL = 'https://mozilla.bango.net'
BANGO_PAY_URL = BANGO_BASE_URL + '/mozpayments/?bcid=%s'
BANGO_LOGOUT_URL = '%s/mozpayments/logout/' % BANGO_BASE_URL

VERBOSE_LOGGING = True

STATSD_HOST = private.STATSD_HOST
STATSD_PORT = private.STATSD_PORT
STATSD_PREFIX = private.STATSD_PREFIX
UUID_HMAC_KEY = private.UUID_HMAC_KEY

ENCRYPTED_COOKIE_KEY = private.ENCRYPTED_COOKIE_KEY

ALLOW_ADMIN_SIMULATIONS = True

base.JS_SETTINGS['tracking_enabled'] = True
NEWRELIC_INI = '/etc/newrelic.d/marketplace.allizom.org-webpay.ini'
