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
