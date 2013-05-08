"""private_base will be populated from puppet and placed in this directory"""
import logging.handlers
import dj_database_url
import private_base as private

from webpay.settings import base

from .. import splitstrip

DOMAIN = 'marketplace-dev.allizom.org'
ALLOWED_HOSTS = [DOMAIN, 'marketplace-altdev.allizom.org']

DATABASES = {}
DATABASES['default'] = dj_database_url.parse(private.DATABASES_DEFAULT_URL)
DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
DATABASES['default']['OPTIONS'] = {'init_command': 'SET storage_engine=InnoDB'}


DATABASES['slave'] = dj_database_url.parse(private.DATABASES_SLAVE_URL)
DATABASES['slave']['ENGINE'] = 'django.db.backends.mysql'
DATABASES['slave']['OPTIONS'] = {'init_command': 'SET storage_engine=InnoDB'}

# Uncomment this and set to all slave DBs in use on the site.
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

# Recipients of traceback emails and other notifications.
ADMINS = ()
MANAGERS = ADMINS

# Debugging displays nice error messages, but leaks memory. Set this to False
# on all server instances and True only for development.
DEBUG = TEMPLATE_DEBUG = False

# Is this a development instance? Set this to True on development/master
# instances and False on stage/prod.
DEV = True

# By default, BrowserID expects your app to use http://127.0.0.1:8000
# Uncomment the following line if you prefer to access your app via localhost
# SITE_URL = 'http://localhost:8000'
SITE_URL = 'https://' + DOMAIN
MARKETPLACE_URL = SITE_URL
MARKETPLACE_OAUTH = {'key': private.MARKETPLACE_OAUTH_KEY,
                     'secret': private.MARKETPLACE_OAUTH_SECRET}

#LOGIN_URL = '/mozpay'

# Playdoh ships with Bcrypt+HMAC by default because it's the most secure.
# To use bcrypt, fill in a secret HMAC key. It cannot be blank.
HMAC_KEYS = private.HMAC_KEYS

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(base.BASE_PASSWORD_HASHERS, HMAC_KEYS)

# Make this unique, and don't share it with anybody.  It cannot be blank.
SECRET_KEY = private.SECRET_KEY

# Should robots.txt allow web crawlers?  Set this to True for production
ENGAGE_ROBOTS = False

## Celery
BROKER_URL = private.BROKER_URL
CELERY_IGNORE_RESULT = True
CELERY_DISABLE_RATE_LIMITS = True
CELERYD_PREFETCH_MULTIPLIER = 1

## Log settings

SYSLOG_TAG = private.SYSLOG_TAG
#LOGGING = dict(loggers=dict(playdoh = {'level': logging.DEBUG}))

# Common Event Format logging parameters
#CEF_PRODUCT = 'Playdoh'
#CEF_VENDOR = 'Mozilla'

# Uncomment this line if you are running a local development install without
# HTTPS to disable HTTPS-only cookies.
SESSION_COOKIE_SECURE = True

DOMAIN = 'marketplace-dev.allizom.org'
ISSUER = DOMAIN
NOTIFY_ISSUER = DOMAIN
VERBOSE_LOGGING = True

KEY = DOMAIN
SECRET = private.SECRET

SOLITUDE_URL = 'https://payments-dev.allizom.org'
SOLITUDE_OAUTH = {'key': private.SOLITUDE_OAUTH_KEY,
                  'secret': private.SOLITUDE_OAUTH_SECRET}

SENTRY_DSN = private.SENTRY_DSN

STATSD_HOST = private.STATSD_HOST
STATSD_PORT = private.STATSD_PORT
STATSD_PREFIX = private.STATSD_PREFIX
