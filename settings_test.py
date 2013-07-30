# This file overrides what's in your webpay/settings/local.py while
# testing.

CELERY_ALWAYS_EAGER = True

# This tells the runner to skip the Solitude client lib tests.
# If you set this to a URL it should look like http://localhost:9000
# but you probably don't want to use your local dev server.
SOLITUDE_URL = None

# A bug in jingo, it will only send the signal to allow test cases to properly
# inspect the result if this is set.
TEMPLATE_DEBUG = True

# We want to act as if we are hitting Solitude APIs even though it will
# be intercepted by mock objects.
FAKE_PAYMENTS = False

# This is the domain that the tests use, setting this removes a warning that
# persona throws.
SITE_URL = 'http://testserver'

ALLOW_SIMULATE = True

BROWSERID_DOMAIN = 'nowhereatall.org'
BROWSERID_UNVERIFIED_ISSUER = BROWSERID_DOMAIN
BROWSERID_VERIFICATION_URL = 'https://%s/verify' % BROWSERID_DOMAIN
ONLY_SIMULATIONS = False
USE_PRODUCT_ICONS = True

# Blockage will prevent us calling this, but we should point it to somewhere.
MARKETPLACE_URL = SOLITUDE_URL = 'http://example.com'

# If you want test this, do so explicitly in the tests.
USER_WHITELIST = []
UUID_HMAC_KEY = 'this is a test value'

ALLOW_ADMIN_SIMULATIONS = True
