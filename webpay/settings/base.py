from funfactory.settings_base import *

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'webpay'

# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = list(INSTALLED_APPS) + [
    'webpay.base',  # Needed for global templates, etc.
    'webpay.pay',
    'webpay.services',
    'tower'
]

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/mozpay/media/'

# A list of our CSS and JS assets for jingo-minify.
MINIFY_BUNDLES = {
    'css': {
        'pay': (
            'css/pay/pay.less',
        ),
    },
    'js': {
        'pay': (
            'js/lib/jquery-1.8.js',
            'js/lib/underscore.js',
            'js/lib/format.js',
            'js/pay/pay.js',
        ),
    }
}

# jingo-minify: Style sheet media attribute default
CSS_MEDIA_DEFAULT = 'all'

# Tell jingo-minify to use the media URL instead.
JINGO_MINIFY_USE_STATIC = False

# LESS CSS OPTIONS (Debug only)
LESS_PREPROCESS = False  # Compile LESS with Node, rather than client-side JS?
LESS_LIVE_REFRESH = False  # Refresh the CSS on save?
LESS_BIN = 'lessc'
UGLIFY_BIN = 'uglify'
CLEANCSS_BIN = 'cleancss'

LOCALE_PATHS = (
    os.path.join(ROOT, PROJECT_MODULE, 'locale'),
)

# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = [
    'admin',
    'registration',
]

# BrowserID configuration
AUTHENTICATION_BACKENDS = [
    'django_browserid.auth.BrowserIDBackend',
    'django.contrib.auth.backends.ModelBackend',
]

SITE_URL = 'http://localhost:8000'
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = 'examples.home'
LOGIN_REDIRECT_URL_FAILURE = 'examples.home'

TEMPLATE_CONTEXT_PROCESSORS = list(TEMPLATE_CONTEXT_PROCESSORS) + [
    'jingo_minify.helpers.build_ids',
    'django_browserid.context_processors.browserid_form',
    'webpay.base.context_processors.static_url',
]

# Should robots.txt deny everything or disallow a calculated list of URLs we
# don't want to be crawled?  Default is false, disallow everything.
# Also see http://www.google.com/support/webmasters/bin/answer.py?answer=93710
ENGAGE_ROBOTS = False

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

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

LOGGING = dict(loggers = dict(playdoh = {'level': logging.DEBUG},
                              w = {'handlers': ['console', 'unicode']}),
               handlers = {'unicode': {'class':
                                       'webpay.unicode_log.UnicodeHandler'}})


MIDDLEWARE_CLASSES = (
    'webpay.base.middleware.LocaleMiddleware',
    'multidb.middleware.PinningRouterMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware', # Must be after auth middleware.
    'django.contrib.messages.middleware.MessageMiddleware',
    'commonware.middleware.FrameOptionsHeader',
    'mobility.middleware.DetectMobileMiddleware',
    'mobility.middleware.XMobileMiddleware',
)

# This is the key and secret for purchases, our special marketplace key and
# secret for selling apps.
KEY = ''
SECRET = ''

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

# When False, the developer can toggle HTTPS on/off.
# This is useful for development and testing.
INAPP_REQUIRE_HTTPS = True
