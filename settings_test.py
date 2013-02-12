# This file overrides what's in your webpay/settings/local.py while
# testing.

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
TEST_PIN_UI = False
