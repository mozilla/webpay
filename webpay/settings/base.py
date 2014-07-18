import logging.handlers
from urlparse import urlparse

from funfactory.settings_base import *

host = os.environ.get('MARKETPLACE_URL', 'http://localhost')

###############################################################################
# Django settings
#
# See https://docs.djangoproject.com/en/dev/ref/settings/ for info.
#
ALLOWED_HOSTS = []

AUTHENTICATION_BACKENDS = []

# We don't actually need a database, this is the smallest and simplest
# configuration we can get away with.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

DEBUG = True
DEBUG_PROPAGATE_EXCEPTIONS = True

INSTALLED_APPS = [
    # Local apps
    'funfactory',  # Content common to most playdoh-based apps.

    'tower',  # for ./manage.py extract (L10n)
    'django_browserid',

    # Django contrib apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    # Third-party apps, patches, fixes
    'commonware.response.cookies',
    'djcelery',
    'django_nose',
    'session_csrf',

    # L10n
    'product_details',

    # Webpay apps.
    'webpay.auth',
    'webpay.base',  # Needed for global templates, etc.
    'webpay.bango',
    'webpay.pay',
    'webpay.provider',
    'webpay.pin',
    'webpay.services',
    'webpay.spa',
    'raven.contrib.django',
    'jingo_minify',
]

LOCALE_PATHS = (
    os.path.join(ROOT, 'webpay', 'locale'),
)

LOGGING = {
    'formatters': {
        'webpay': {
            '()': 'webpay.base.logger.WebpayFormatter',
            'format':
                '%(name)s:%(levelname)s '
                '%(REMOTE_ADDR)s:%(TRANSACTION_ID)s:%(CLIENT_ID)s '
                '%(message)s :%(pathname)s:%(lineno)s'
        }
    },
    'loggers': {
        'django_browserid': {
            'level': logging.DEBUG,
            'handlers': ['console', 'unicodesyslog'],
            'formatter': 'webpay',
        },
        'encrypted_cookies': {
            'level': logging.INFO,
            'handlers': ['console', 'unicodesyslog'],
            'formatter': 'webpay',
        },
        # This gives us "zamboni" logging such as the celeryutils logger.
        'z': {
            'level': logging.ERROR,
            'handlers': ['console', 'unicodesyslog', 'sentry'],
            'formatter': 'webpay',
        },
        # This gives us webpay logging.
        'w': {
            'level': logging.DEBUG,
            'handlers': ['console', 'unicodesyslog', 'sentry'],
            'formatter': 'webpay',
        },
        # This sends exceptions to Sentry.
        'django.request': {
            'level': 'INFO',
            'handlers': ['console', 'unicodesyslog', 'sentry'],
        },
        'requests.packages.urllib3.connectionpool': {
            'level': 'ERROR',
        },
        'newrelic': {
            'level': 'ERROR'
        }
    },
    'handlers': {
        'unicodesyslog': {
            'class': 'mozilla_logger.log.UnicodeHandler',
            'facility': logging.handlers.SysLogHandler.LOG_LOCAL7,
            'formatter': 'prod',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
    },
}

LOGIN_URL = 'pay.lobby'
LOGIN_REDIRECT_URL = 'pay.lobby'
LOGIN_REDIRECT_URL_FAILURE = 'pay.lobby'

MEDIA_URL = '/mozpay/media/'

MIDDLEWARE_CLASSES = (
    'webpay.base.middleware.CSPMiddleware',
    'django_statsd.middleware.GraphiteRequestTimingMiddleware',
    'django_statsd.middleware.GraphiteMiddleware',
    'webpay.base.middleware.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',  # Must be after auth middleware.
    'django.contrib.messages.middleware.MessageMiddleware',
    'commonware.middleware.FrameOptionsHeader',
    'webpay.base.middleware.LogJSONerror',
    'webpay.base.middleware.CEFMiddleware',
    'django_paranoia.middleware.Middleware',
    'django_paranoia.sessions.ParanoidSessionMiddleware',
    'webpay.base.logger.LoggerMiddleware',
)

MINIFY_BUNDLES = {
    'css': {
        'pay/pay': (
            'css/pay/normalize.styl',
            'css/pay/util.styl',
            'css/pay/fonts.styl',
            'css/pay/throbber.styl',
            'css/pay/messages.styl',
            'css/pay/pay.styl',
            'css/pay/simulate.styl',
        ),
    },
    'js': {
        'pay': (
            'js/lib/jquery-1.8.js',
            'js/lib/require.js',
            'js/settings.js',
            'js/lib/underscore.js',
            'js/lib/format.js',
            'js/lib/longtext.js',
            'js/lib/tracking.js',
            'js/lib/raven.min.js',
            'js/lib/raven-proxy.js',

            # These are modules used by others.
            # The order is important, do not alphabetize.
            'js/raven-init.js',
            'js/cli.js',
            'js/id.js',
            'js/auth.js',
            'js/lib/l10n.js',
            'js/pay/bango.js',

            # These are top-level modules.
            'js/pay/messages.js',
            'js/pay/pay.js',
            'js/pay/wait.js',
            'js/pay/cancel.js',
            'js/pin/pin.js',
            'js/pin/reset.js',
        ),
    }
}

ROOT_URLCONF = 'webpay.urls'

SECRET_KEY = 'please change this'

SESSION_ENGINE = 'encrypted_cookies'

# Custom name of session cookie.
# This must be a non-default so it doesn't collide with zamboni on the same
# subdomain.
SESSION_COOKIE_NAME = 'webpay_sessionid'

# All the webpay stuff is under a custom domain.
SESSION_COOKIE_PATH = '/mozpay/'

# Limiting the session cookie down to a small number prevents people coming
# back later with valid transactions and session. It does mean people inactive
# for more than this time will have to start again though.
SESSION_COOKIE_AGE = 60 * 60

SESSION_COOKIE_SECURE = False

# Needed to serve the media out for development servers.
TEMPLATE_DEBUG = DEBUG

TEST_RUNNER = 'test_utils.runner.NoDBTestSuiterunner'

##############################################################################
# Celery settings
#
CELERY_ALWAYS_EAGER = True

###############################################################################
# Project settings
#
# Moved up here because other things depend upon it.
#
# The domain of the webpay server. Example: webpay.somewhere.org.
DOMAIN = urlparse(host).netloc

# When True, allow Marketplace admins and reviewers to force a simulated
# payment if needed.
ALLOW_ADMIN_SIMULATIONS = True

ALLOW_ANDROID_PAYMENTS = True

# When True, developers can simulate payments by signing a JWT with a simulate
# attribute in the request.
ALLOW_SIMULATE = True

ALLOW_TARAKO_PAYMENTS = False

# The schemes that are allowed in callbacks.
# Historically, app postbacks were required to be HTTPS in prod but we reversed
# that decision. See bug 862588.
ALLOWED_CALLBACK_SCHEMES = ['http', 'https']

# When passing a simulate request, the result must match one of these.
ALLOWED_SIMULATIONS = ('postback', 'chargeback')

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

# Custom anon CSRF cookie name.
# This is to avoid collisions with zamboni when on the same subdomain.
ANON_COOKIE = 'webpay_anoncsrf'

# This is the key and secret for purchases, our special marketplace key and
# secret for selling apps.
APP_PURCHASE_KEY = KEY = DOMAIN

# This is the key and secret for purchases, our special marketplace key and
# secret for selling apps.
APP_PURCHASE_SECRET = SECRET = 'please change this'

# We won't be persisting users in the DB.
BROWSERID_CREATE_USER = False

# Control which Persona server you use for logins.
# This is useful for switching to a development Persona server.
BROWSERID_DOMAIN = 'login.persona.org'
BROWSERID_JS_URL = 'https://%s/include.js' % BROWSERID_DOMAIN
# We only trust one issuer to grant us unverified emails.
# If UNVERIFIED_ISSUER is set to None, forceIssuer will not
# be sent to the client or the verifier.
BROWSERID_UNVERIFIED_ISSUER = 'firefoxos.persona.org'
BROWSERID_VERIFICATION_URL = 'https://%s/verify' % BROWSERID_DOMAIN

CACHEBUST_IMGS = True

# A cache nuggets setting, that hasn't been updated to use the
# new PREFIX in the CACHE setttings. Overridden on all prod servers.
CACHE_PREFIX = 'webpay'

CLEANCSS_BIN = 'cleancss'

# When True, compress session cookie data with zlib to improve network
# performance and avoid maxing out HTTP header length.
COMPRESS_ENCRYPTED_COOKIE = True

# CSP Settings
CSP_REPORT_URI = '/mozpay/services/csp/report'
CSP_POLICY_URI = '/mozpay/services/csp/policy'
CSP_REPORT_ONLY = True

CSP_ALLOW = ("'self'",)

# Note: STATIC_URL will be added to these in the middleware.
CSP_IMG_SRC = (
    "'self'",
    'https://ssl.google-analytics.com',
    'data:'
)
CSP_SCRIPT_SRC = (
    "'self'",
    'https://%s' % BROWSERID_DOMAIN,
    'https://ssl.google-analytics.com',
)
CSP_STYLE_SRC = (
    "'self'",
    # Because CSRF and persona both use style="".
    "'unsafe-inline'",
    'https://static.login.persona.org'
)
CSP_OBJECT_SRC = ("'none'",)
CSP_MEDIA_SRC = ("'none'",)
CSP_FRAME_SRC = (
    'https://ssl.google-analytics.com',
    'https://%s' % BROWSERID_DOMAIN,
)
CSP_FONT_SRC = ("'self'",)

# When running in DEBUG mode, we assume you are running locally
# and are not using SSL. If that's the case, resources might load
# as http too.
if DEBUG:
    for key in ('CSP_IMG_SRC', 'CSP_MEDIA_SRC', 'CSP_SCRIPT_SRC'):
        values = locals()[key]
        new = []
        for value in values:
            if value.startswith('https://'):
                new.append(value.replace('https://', 'http://'))
        locals()[key] = tuple(list(values) + new)


# Custom name for csrf cookie.
# This must be a non-default value so it doesn't collide with zamboni on the
# same subdomain.
CSRF_COOKIE_NAME = 'webpay_csrftoken'

CSS_MEDIA_DEFAULT = 'all'

DJANGO_PARANOIA_REPORTERS = [
    'django_paranoia.reporters.cef_',
]

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS['messages'] = [
    ('webpay/**.py',
        'tower.management.commands.extract.extract_tower_python'),
    ('webpay/**/templates/**.html',
        'tower.management.commands.extract.extract_tower_template'),
    ('templates/**.html',
        'tower.management.commands.extract.extract_tower_template'),
]

# Set the zlib level for compression.
ENCRYPTED_COOKIE_COMPRESSION_LEVEL = 6

# This string is used for encrypting session cookies. It should be at least 64
# bytes and should be set to a random value. If you leave this empty,
# SECRET_KEY is used.
ENCRYPTED_COOKIE_KEY = ''

# Should robots.txt deny everything or disallow a calculated list of URLs we
# don't want to be crawled?  Default is false, disallow everything.
# Also see http://www.google.com/support/webmasters/bin/answer.py?answer=93710
ENGAGE_ROBOTS = False

# The issuer of the special marketplace app purchase JWTs.
ISSUER = DOMAIN

HAS_SYSLOG = not DEBUG

# Temporary, this should be going into solitude.
INAPP_KEY_PATHS = {}

# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = [
    'admin',
    'registration',
]

# Tell jingo-minify to use the media URL instead.
JINGO_MINIFY_USE_STATIC = False

JS_SETTINGS = {
    # Allow tracking of events.
    'action_tracking_enabled': True,
    # Whether to ignore the users 'Do Not Track' settings.
    'dnt_override': False,
    # The category used in all event tracking.
    'ga_tracking_category': 'Consumer Payment Flow',
    # The Google Analytics tracking ID for this app.
    'ga_tracking_id': 'UA-36116321-6',
    # Turn GA tracking on/off wholesale.
    'tracking_enabled': False,
    # Timeout for logout (Default 45s).
    'logout_timeout': 45000,
    # Timeout for logins (Default 90s).
    'login_timeout': 90000,
    # General Ajax timeout (Default 45s).
    'ajax_timeout': 45000,
    # Wait timeout (Default 60s).
    'wait_timeout': 60000,
    # This is the poll interval (in milleseconds) used while waiting for
    # something to happen.
    'poll_interval': 1000,
    # Raven error logging
    # ex: http://none@zamboni.localhost/api/v1/fireplace/report_error/12345
    # Please note that the leading 'none@' is required
    # The trailing integer '12345' is the sentry account id which
    # is found in a sentry DSN
    # ex: https://<user>:<pass>@app.getsentry.com/<sentry_account_id>
    'zamboni_raven_url': '',
}

# This is the URL to the marketplace.
MARKETPLACE_URL = host

# The OAuth config from the marketplace.
MARKETPLACE_OAUTH = {'key': '', 'secret': ''}

# Configure our test runner for some nice test output.
NOSE_PLUGINS = [
    'nosenicedots.NiceDots',
    'blockage.plugins.NoseBlockage',
]

NOSE_ARGS = [
    '--logging-clear-handlers',
    '--logging-level=DEBUG',
    '--with-nicedots',
    '--with-blockage',
    '--http-whitelist=""',
]

# The issuer of all notifications (i.e. the webpay server).
NOTIFY_ISSUER = DOMAIN

# New Relic is configured here.
NEWRELIC_INI = None

# If True, only simulated payments can be processed. All other requests will
# result in an error.
ONLY_SIMULATIONS = False

# The pay URL is the starting page of the payment screen.
# It will receive one substitution: the uid_pay value. For example, this is the
# Billing Configuration ID in Bangoland.
PAY_URLS = {
    'bango': {
        'base': 'https://mozilla.bango.net',
        'pay': '/mozpayments/?bcid={uid_pay}',
        # This is used by the UI to clear all Bango cookies.
        'logout': '/mozpayments/logout/',
    },
    'reference': {
        'base': 'https://zippy.paas.allizom.org',
        'pay': '/payment/start?tx={uid_pay}',
        'logout': '/users/reset',
    },
    'boku': {
        'base': '',
        'pay': '',
        'logout': ''
    }
}

# Which payment provider to use on the backend, it must be one of
# PAYMENT_PROVIDERS.
PAYMENT_PROVIDER = 'reference'
PAYMENT_PROVIDERS = ('bango', 'boku', 'reference')

# This is the time that a user has to buy more stuff before having to enter
# their PIN in again in seconds.
# Disable PIN unlocking because of bug 1000877.
PIN_UNLOCK_LENGTH = 0

# Number of retries on a payment postback.
POSTBACK_ATTEMPTS = 5

# Amount of seconds between each payment postback attempt.
POSTBACK_DELAY = 300

# In production, all locales must be whitelisted for use, regardless of the
# existence of po files.
PROD_LANGUAGES = (
    'af',
    'bg',
    'ca',
    'cs',
    'da',
    'de',
    'el',
    'en-US',
    'es',
    'eu',
    'fi',
    'fr',
    'fy-NL',
    'ga-IE',
    'hr',
    'hu',
    'id',
    'it',
    'ja',
    'ko',
    'mk',
    'my',
    'nl',
    'pl',
    'pt-BR',
    'pt-PT',
    'ro',
    'ru',
    'sk',
    'sl',
    'sq',
    'sr',
    'sr-Latn',
    'srp',
    'sv-SE',
    'te',
    'th',
    'ur',
    'vi',
    'zh-CN',
    'zh-TW',
)

# Maximum length of a product description. This is used to truncate long
# descriptions so that they do not break things like session cookies.
PRODUCT_DESCRIPTION_LENGTH = 255

# Height/width size of product icon images.
PRODUCT_ICON_SIZE = 64

PROJECT_MODULE = 'webpay'

# Maximum value for "short" fields in a product JWT. These are fields (like
# 'name') that have an implied short length. Values that exceed the maximum will
# trigger form errors.
SHORT_FIELD_MAX_LENGTH = 255

# This is the typ for signature checking JWTs.
# This is used to integrate with Marketplace and other apps.
SIG_CHECK_TYP = 'mozilla/payments/sigcheck/v1'

# When not None, this is a dict of mcc and mnc to simulate a specific mobile
# network. This overrides the client side network detection.
# Example: {'mcc': '123', 'mnc': '45'}
# Use this setting carefully!
SIMULATED_NETWORK = None

SITE_URL = host.rstrip('/')

# This is the URL lib.solitude.api uses to connect to the pay server. If this
# is none the solitude api tests don't run as we currently don't have a mock
# server for it.
SOLITUDE_URL = os.environ.get('SOLITUDE_URL', 'http://localhost:2602')

# The OAuth tokens for solitude.
SOLITUDE_OAUTH = {'key': '', 'secret': ''}

SPARTACUS_BUILD_ID_KEY = 'spartacus-build-id'
SPARTACUS_STATIC = 'http://localhost:7777'

# Spartacus path settings.
SPA_BASE_URL = '/mozpay/spa/'
SPA_ENABLE = False
SPA_ENABLE_URLS = False
SPA_URLS = [
    'create-pin',
    'enter-pin',
    'locked',
    'login',
    'reset-pin',
    'reset-start',
    'wait-for-tx',
    'was-locked'
]
SPA_USE_MIN_JS = True

# SPA App settings. These are merged into the app's settings.js.
# This allows us to specify different settings for -dev/stage/prod
SPA_SETTINGS = {
    # Turn UA tracking on/off wholesale.
    'ua_tracking_enabled': False,
    # These are payment provider buy flow sites that Spartacus
    # is allowed to redirect to.
    'validRedirSites': [
        'http://mozilla.bango.net',
        'https://mozilla.bango.net',
        'https://buy.boku.com',
        # Allow redirects to Zippy which typically would be accessible
        # via your local host name on its own port.
        SITE_URL,
    ]
}

STATSD_CLIENT = 'django_statsd.clients.normal'

# Stylus / Uglify / CleanCSS.
STYLUS_BIN = 'stylus'

TEMPLATE_CONTEXT_PROCESSORS = list(TEMPLATE_CONTEXT_PROCESSORS) + [
    'jingo_minify.helpers.build_ids',
    'django_browserid.context_processors.browserid',
    'webpay.base.context_processors.defaults',
]

# Special just for front-end folks! When True, it lets you hit the main page
# without a JWT. You can create/enter PINs but it won't let you get very far
# beyond that.
TEST_PIN_UI = False

UGLIFY_BIN = 'uglifyjs'

# When True, use the marketplace API to get product icons.
USE_PRODUCT_ICONS = True

# Secret key string to use in UUID HMACs which are derived from Persona emails.
# This must not be blank in production and should be more than 32 bytes long.
UUID_HMAC_KEY = ''

# Warning that this server is really only for testing.
USAGE_WARNING = False

# If empty, all users will be allowed through.
# If not empty, each string will be compiled as a regular expression
# and the email from persona checked using match, not search. If any of the
# expressions match, the user will be let through.
USER_WHITELIST = []

# Set this to True to get nice long verbose messages.
VERBOSE_LOGGING = False

IN_TEST_SUITE = False
