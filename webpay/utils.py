from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def validate_settings():
    """
    Validate that if not in DEBUG mode, key settings have been changed.
    """
    if settings.DEBUG or settings.IN_TEST_SUITE:
        return

    # Things that values must not be.
    for key, value in [
            ('SECRET_KEY', 'please change this'),
            ('ENCRYPTED_COOKIE_KEY', ''),
            ('UUID_HMAC_KEY', ''),
            ('SESSION_COOKIE_SECURE', False),
            ('APP_PURCHASE_SECRET', 'please change this'),
            ('SECRET', 'please change this')]:
        if getattr(settings, key) == value:
            raise ImproperlyConfigured('{0} must be changed from default'
                                       .format(key))


def update_csp():
    """
    After settings, including DEBUG has loaded, see if we need to update CSP.
    """
    for key in ('CSP_IMG_SRC', 'CSP_MEDIA_SRC', 'CSP_SCRIPT_SRC'):
        values = getattr(settings, key)
        new = set()
        for value in values:
            # If we are in debug mode, mirror any HTTPS resources as a
            # HTTP url.
            if value.startswith('https://') and settings.DEBUG:
                res = value.replace('https://', 'http://')
                for v in value, res:
                    new.add(v)
                continue
            # If there's a HTTP url in there and we are not in debug mode
            # don't add it in.
            elif value.startswith('http://') and not settings.DEBUG:
                continue
            # Add in anything like 'self'.
            else:
                new.add(value)

        setattr(settings, key, tuple(new))
