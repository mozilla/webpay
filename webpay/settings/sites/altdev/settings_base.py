"""private_base will be populated from puppet and placed in this directory"""
import dj_database_url
import private_base as private

from webpay.settings import base

from .. import splitstrip

DOMAIN = 'marketplace-altdev.allizom.org'
ALLOWED_HOSTS = [DOMAIN]

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
BROWSERID_AUDIENCES = [SITE_URL]

STATIC_URL_DOMAIN = 'marketplace-altdev-cdn.allizom.org'
STATIC_URL = 'https://%s/' % STATIC_URL_DOMAIN
MEDIA_URL = STATIC_URL + 'mozpay/media/'

# Playdoh ships with Bcrypt+HMAC by default because it's the most secure.
# To use bcrypt, fill in a secret HMAC key. It cannot be blank.
HMAC_KEYS = private.HMAC_KEYS

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(base.BASE_PASSWORD_HASHERS, HMAC_KEYS)

# Make this unique, and don't share it with anybody.  It cannot be blank.
SECRET_KEY = private.SECRET_KEY

# Should robots.txt allow web crawlers?  Set this to True for production
ENGAGE_ROBOTS = False

# Celery
BROKER_URL = private.BROKER_URL
CELERY_ALWAYS_EAGER = False
CELERY_IGNORE_RESULT = True
CELERY_DISABLE_RATE_LIMITS = True
CELERYD_PREFETCH_MULTIPLIER = 1

# Log settings

SYSLOG_TAG = private.SYSLOG_TAG
# LOGGING = dict(loggers=dict(playdoh = {'level': logging.DEBUG}))

# Uncomment this line if you are running a local development install without
# HTTPS to disable HTTPS-only cookies.
SESSION_COOKIE_SECURE = True

ISSUER = DOMAIN
NOTIFY_ISSUER = DOMAIN
VERBOSE_LOGGING = True

APP_PURCHASE_KEY = KEY = DOMAIN
APP_PURCHASE_SECRET = SECRET = private.SECRET

SOLITUDE_URL = 'https://payments-altdev.allizom.org'
SOLITUDE_OAUTH = {'key': private.SOLITUDE_OAUTH_KEY,
                  'secret': private.SOLITUDE_OAUTH_SECRET}

SENTRY_DSN = private.SENTRY_DSN

STATSD_HOST = private.STATSD_HOST
STATSD_PORT = private.STATSD_PORT
STATSD_PREFIX = private.STATSD_PREFIX
UUID_HMAC_KEY = private.UUID_HMAC_KEY

# Bypass Bango on Dev when True.
FAKE_PAYMENTS = False

ENCRYPTED_COOKIE_KEY = private.ENCRYPTED_COOKIE_KEY

ALLOW_ADMIN_SIMULATIONS = True

base.JS_SETTINGS['tracking_enabled'] = True
base.JS_SETTINGS['zamboni_raven_url'] = (
    'https://none@marketplace-altdev.allizom.org/'
    'api/v1/fireplace/report_error/3')

NEWRELIC_INI = None

# reference == Zippy.
PAYMENT_PROVIDER = 'reference'


PAY_URLS = {
    # Talk to Bango Test.
    'bango': {
        'base': 'http://mozilla.test.bango.org',
        'pay': '/mozpayments/?bcid={uid_pay}',
        'logout': '/mozpayments/logout/',
    },
    'reference': {
        'base': 'https://zippy.paas.allizom.org',
        'pay': '/payment/start?tx={uid_pay}',
        'logout': '/users/reset',
    },
}

SPARTACUS_STATIC = 'https://%s/mozpay/spa' % STATIC_URL_DOMAIN

SPA_SETTINGS = base.SPA_SETTINGS
SPA_SETTINGS['validRedirSites'].append('https://zippy.paas.allizom.org')
SPA_SETTINGS['ua_tracking_enabled'] = True

NOSE_PLUGINS = []

FXA_CLIENT_ID = private.FXA_CLIENT_ID
FXA_CLIENT_SECRET = private.FXA_CLIENT_SECRET
