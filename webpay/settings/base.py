import logging.handlers

from funfactory.settings_base import *

ALLOWED_HOSTS = []

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'webpay'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

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
    'webpay.pin',
    'webpay.services',
    'raven.contrib.django',
    'jingo_minify',
]

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/mozpay/media/'

# A list of our CSS and JS assets for jingo-minify.
MINIFY_BUNDLES = {
    'css': {
        'pay/pay': (
            'css/pay/normalize.styl',
            'css/pay/util.styl',
            'css/pay/fonts.styl',
            'css/pay/throbber.styl',
            'css/pay/messages.styl',
            'css/pay/pay.styl',
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

            # These are modules used by others.
            # The order is important, do not alphabetize.
            'js/cli.js',
            'js/id.js',
            'js/auth.js',
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

# jingo-minify: Style sheet media attribute default
CSS_MEDIA_DEFAULT = 'all'

# Tell jingo-minify to use the media URL instead.
JINGO_MINIFY_USE_STATIC = False

# Cache-bust images in the CSS.
CACHEBUST_IMGS = True

# Stylus / Uglify / CleanCSS.
STYLUS_BIN = 'stylus'
UGLIFY_BIN = 'uglifyjs'
CLEANCSS_BIN = 'cleancss'

LOCALE_PATHS = (
    os.path.join(ROOT, PROJECT_MODULE, 'locale'),
)

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


# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = [
    'admin',
    'registration',
]

# BrowserID configuration
AUTHENTICATION_BACKENDS = [
    #'django_browserid.auth.BrowserIDBackend',
    #'django.contrib.auth.backends.ModelBackend',
]

SITE_URL = 'http://localhost:8000'
LOGIN_URL = 'pay.lobby'
LOGIN_REDIRECT_URL = 'pay.lobby'
LOGIN_REDIRECT_URL_FAILURE = 'pay.lobby'

# We won't be persisting users in the DB.
BROWSERID_CREATE_USER = False

TEMPLATE_CONTEXT_PROCESSORS = list(TEMPLATE_CONTEXT_PROCESSORS) + [
    'jingo_minify.helpers.build_ids',
    'django_browserid.context_processors.browserid',
    'webpay.base.context_processors.defaults',
]

# Should robots.txt deny everything or disallow a calculated list of URLs we
# don't want to be crawled?  Default is false, disallow everything.
# Also see http://www.google.com/support/webmasters/bin/answer.py?answer=93710
ENGAGE_ROBOTS = False

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

# Custom name for csrf cookie.
# This must be a non-default value so it doesn't collide with zamboni on the
# same subdomain.
CSRF_COOKIE_NAME = 'webpay_csrftoken'

# Custom anon CSRF cookie name.
# This is to avoid collisions with zamboni when on the same subdomain.
ANON_COOKIE = 'webpay_anoncsrf'

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS['messages'] = [
    ('%s/**.py' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_python'),
    ('%s/**/templates/**.html' % PROJECT_MODULE,
        'tower.management.commands.extract.extract_tower_template'),
    ('templates/**.html',
        'tower.management.commands.extract.extract_tower_template'),
]

HAS_SYSLOG = True  # syslog is used if HAS_SYSLOG and NOT DEBUG.
# See settings/local.py for SYSLOG_TAG, etc
LOGGING = {
    'formatters': {
        'webpay': {
            '()': 'webpay.base.logger.WebpayFormatter',
            'format':
                '%(name)s:%(levelname)s '
                '%(REMOTE_ADDR)s:%(TRANSACTION_ID)s '
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

STATSD_CLIENT = 'django_statsd.clients.normal'

DJANGO_PARANOIA_REPORTERS = [
    'django_paranoia.reporters.cef_',
]

SESSION_ENGINE = 'encrypted_cookies'

# Custom name of session cookie.
# This must be a non-default so it doesn't collide with zamboni on the same
# subdomain.
SESSION_COOKIE_NAME = 'webpay_sessionid'

# All the webpay stuff is under a custom domain.
SESSION_COOKIE_PATH = '/mozpay/'

# Limiting the session cookie down to a small number prevents people coming back
# later with valid transactions and session. It does mean people inactive for
# more than this time will have to start again though.
SESSION_COOKIE_AGE = 60 * 10

# By default, celery is active.
# If you need to disable it, make this True in your local settings.
CELERY_ALWAYS_EAGER = False  # required to activate celeryd

# This is the key and secret for purchases, our special marketplace key and
# secret for selling apps.
KEY = 'marketplace'  # would typically be a URL
SECRET = ''

# Marketplace's postback/chargeback URLs where app purchase JWT notifications
# are sent.
MKT_POSTBACK = 'https://marketplace-dev.allizom.org/services/bluevia/postback'
MKT_CHARGEBACK = 'https://marketplace-dev.allizom.org/services/bluevia/chargeback'

# The domain of the webpay server. Example: webpay.somewhere.org
DOMAIN = 'localhost'

# The issuer of the special marketplace app purchase JWTs.
ISSUER = DOMAIN

# The issuer of all notifications (i.e. the webpay server).
NOTIFY_ISSUER = DOMAIN

# Temporary, this should be going into solitude.
INAPP_KEY_PATHS = {}

# Set this to True to get nice long verbose messages.
VERBOSE_LOGGING = False

# This is the URL lib.solitude.api uses to connect to the pay server. If this
# is none the solitude api tests don't run as we currently don't have a mock
# server for it.
SOLITUDE_URL = None

# The OAuth tokens for solitude.
SOLITUDE_OAUTH = {'key': '', 'secret': ''}

# Instead of doing a real Bango pay flow, redirect to a fake placeholder
# for the Bango flow when True.
FAKE_PAYMENTS = False

# Control which Persona server you use for logins.
# This is useful for switching to a development Persona server.

BROWSERID_DOMAIN = 'login.persona.org'
# We only trust one issuer to grant us unverified emails.
# If UNVERIFIED_ISSUER is set to None, forceIssuer will not
# be sent to the client or the verifier.
BROWSERID_UNVERIFIED_ISSUER = 'firefoxos.persona.org'
BROWSERID_VERIFICATION_URL = 'https://%s/verify' % BROWSERID_DOMAIN
BROWSERID_JS_URL = 'https://%s/include.js' % BROWSERID_DOMAIN

BANGO_BASE_URL = 'http://mozilla.test.bango.org'

# This is the URL for the bango payment screen.
# It will receive one string substitution: the billing configuration ID.
BANGO_PAY_URL = BANGO_BASE_URL + '/mozpayments/?bcid=%s'

# This is used by the UI to clear all Bango cookies.
BANGO_LOGOUT_URL = '%s/mozpayments/logout/' % BANGO_BASE_URL

# This is the URL to the marketplace.
MARKETPLACE_URL = None

# The OAuth config from the marketplace.
MARKETPLACE_OAUTH = {'key': '', 'secret': ''}

# Height/width size of product icon images.
PRODUCT_ICON_SIZE = 64

# When True, use the marketplace API to get product icons.
USE_PRODUCT_ICONS = True

# This is the time that a user has to buy more stuff before having to enter
# their PIN in again in seconds.
PIN_UNLOCK_LENGTH = 300

# The schemes that are allowed in callbacks.
# Historically, app postbacks were required to be HTTPS in prod but we reversed
# that decision. See bug 862588.
ALLOWED_CALLBACK_SCHEMES = ['http', 'https']

# When we are ready to having curling format lists for us, flip this to True.
CURLING_FORMAT_LISTS = False

# Number of retries on a payment postback.
POSTBACK_ATTEMPTS = 5

# Amount of seconds between each payment postback attempt.
POSTBACK_DELAY = 300

# When True, developers can simulate payments by signing a JWT with a simulate
# attribute in the request.
ALLOW_SIMULATE = True

# When passing a simulate request, the result must match one of these.
ALLOWED_SIMULATIONS = ('postback', 'chargeback')

# If True, only simulated payments can be processed. All other requests will
# result in an error.
ONLY_SIMULATIONS = False

# When True, allow Marketplace admins and reviewers to force a simulated payment
# if needed.
ALLOW_ADMIN_SIMULATIONS = False

# Special just for front-end folks! When True, it lets you hit the main page
# without a JWT. You can create/enter PINs but it won't let you get very far
# beyond that.
TEST_PIN_UI = False

# If empty, all users will be allowed through.
# If not empty, each string will be compiled as a regular expression
# and the email from persona checked using match, not search. If any of the
# expressions match, the user will be let through.
USER_WHITELIST = []

# Secret key string to use in UUID HMACs which are derived from Persona emails.
# This must not be blank in production and should be more than 32 bytes long.
UUID_HMAC_KEY = ''

# This string is used for encrypting session cookies. It should be at least 64
# bytes and should be set to a random value. In development (or if you leave
# this empty), SECRET_KEY is used.
#ENCRYPTED_COOKIE_KEY = ''

# When True, compress session cookie data with zlib to improve network
# performance and avoid maxing out HTTP header length.
COMPRESS_ENCRYPTED_COOKIE = True

# Set the zlib level for compression.
ENCRYPTED_COOKIE_COMPRESSION_LEVEL = 6

# Maximum length of a product description. This is used to truncate long
# descriptions so that they do not break things like session cookies.
PRODUCT_DESCRIPTION_LENGTH = 255

# Maximum value for "short" fields in a product JWT. These are fields (like
# 'name') that have an implied short length. Values that exceed the maximum will
# trigger form errors.
SHORT_FIELD_MAX_LENGTH = 255

# This is the typ for signature checking JWTs.
# This is used to integrate with Marketplace and other apps.
SIG_CHECK_TYP = 'mozilla/payments/sigcheck/v1'

# CSP Settings
CSP_REPORT_URI = '/mozpay/services/csp/report'
CSP_POLICY_URI = '/mozpay/services/csp/policy'
CSP_REPORT_ONLY = True

CSP_ALLOW = ("'self'",)

# Note: STATIC_URL will be added to these in the middleware.
CSP_IMG_SRC = ("'self'",
               "https://ssl.google-analytics.com",
               "data:"
              )
CSP_SCRIPT_SRC = ("'self'",
                  "https://%s" % BROWSERID_DOMAIN,
                  "https://ssl.google-analytics.com",
                  )
CSP_STYLE_SRC = ("'self'",
                 # Because CSRF and persona both use style="".
                 "'unsafe-inline'",
                 "https://static.login.persona.org")
CSP_OBJECT_SRC = ("'none'",)
CSP_MEDIA_SRC = ("'none'",)
CSP_FRAME_SRC = ("https://ssl.google-analytics.com",
                 "https://%s" % BROWSERID_DOMAIN,
                )
CSP_FONT_SRC = ("'self'",)

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
}

# New Relic is configured here.
NEWRELIC_INI = None

# Which payment provider to use on the backend.
# Choices: 'bango', 'reference'
# In the future this might be chosen dynamically based on region or something.
PAYMENT_PROVIDER = 'bango'

# When True, Webpay uses a universal payment provider API for the active
# PAYMENT_PROVIDER.
UNIVERSAL_PROVIDER = False
