from .base import *

BROWSERID_DOMAIN = 'localhost:9765'
BROWSERID_JS_URL = '/include.js'
BROWSERID_VERIFICATION_URL = 'http://%s/verify' % BROWSERID_DOMAIN
DATABASES = { 'default': {} }
DEBUG = DEV = TEMPLATE_DEBUG = True
FAKE_PAYMENTS = True
HMAC_KEYS = { '2012-06-06': 'some secret', }
MARKETPLACE_URL = 'http://localhost:9765'
MEDIA_URL = '/mozpay/media/'
SECRET_KEY = 'FAKE'
SESSION_COOKIE_SECURE = False
SITE_URL = ''
SOLITUDE_URL = 'https://mock-solitude.paas.allizom.org/'
TEST_PIN_UI = True


try:
    from .uitestslocal import *
except ImportError, exc:
    pass
