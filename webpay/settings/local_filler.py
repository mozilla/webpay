"""Fake settings

These settings are here so the docs can build on RTD. This file has settings in
local.py that are required just to import the files for building API docs.

"""

SECRET_KEY = 'FAKE'
SESSION_COOKIE_SECURE = False
HMAC_KEYS = {
    '2012-06-06': 'some secret',
}
DATABASES = {
    'default': {}
}
