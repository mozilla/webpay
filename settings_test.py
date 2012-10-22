# This file overrides what's in your webpay/settings/local.py while
# testing.


# This tells the runner to skip the Solitude client lib tests.
# If you set this to a URL it should look like http://localhost:9000
# but you probably don't want to use your local dev server.
SOLITUDE_URL = None
