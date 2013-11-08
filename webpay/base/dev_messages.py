from django.conf import settings
from django.utils import translation

import tower
from tower import ugettext as _


BAD_BANGO_CODE = 'BAD_BANGO_CODE'
BAD_JWT_ISSUER = 'BAD_JWT_ISSUER'
BAD_ICON_KEY = 'BAD_ICON_KEY'
BAD_PRICE_POINT = 'BAD_PRICE_POINT'
BAD_REQUEST = 'BAD_REQUEST'
BAD_SIM_RESULT = 'BAD_SIM_RESULT'
BANGO_ERROR = 'BANGO_ERROR'
EXPIRED_JWT = 'EXPIRED_JWT'
INTERNAL_TIMEOUT = 'INTERNAL_TIMEOUT'
INVALID_JWT = 'INVALID_JWT'
INVALID_JWT_OBJ = 'INVALID_JWT_OBJ'
JWT_DECODE_ERR = 'JWT_DECODE_ERR'
LOGIN_TIMEOUT = 'LOGIN_TIMEOUT'
LOGOUT_TIMEOUT = 'LOGOUT_TIMEOUT'
MALFORMED_URL = 'MALFORMED_URL'
NO_ACTIVE_TRANS = 'NO_ACTIVE_TRANS'
NO_DEFAULT_LOC = 'NO_DEFAULT_LOC'
NO_SIM_REASON = 'NO_SIM_REASON'
NOTICE_ERROR = 'NOTICE_ERROR'
PAY_DISABLED = 'PAY_DISABLED'
RESOURCE_MODIFIED = 'RESOURCE_MODIFIED'
SIM_DISABLED = 'SIM_DISABLED'
SIM_ONLY_KEY = 'SIM_ONLY_KEY'
TRANS_ENDED = 'TRANS_ENDED'
TRANS_TIMEOUT = 'TRANS_TIMEOUT'
UNSUPPORTED_PAY = 'UNSUPPORTED_PAY'
# This string is used to determine the message on Marketplace;
# change it at your peril.
USER_CANCELLED = 'USER_CANCELLED'

SHORT_FIELDS = ('chargebackURL',
                'defaultLocale',
                'id',
                'name',
                'postbackURL',
                'productData')

# Map of field name to 'too long' error code.
SHORT_FIELD_TOO_LONG_CODE = {}

# Convert all short fields into error codes.
# E.G. CHARGEBACKURL_TOO_LONG
for fn in SHORT_FIELDS:
    cd = '{0}_TOO_LONG'.format(fn.upper())
    SHORT_FIELD_TOO_LONG_CODE[fn] = cd


def legend(locale=None):
    """
    Legend of error message codes for developers.

    These codes are used in validation but will be slightly hidden from users
    so as not to cause confusion. The legend is a reference for
    developers.
    """
    old_locale = translation.get_language()
    if locale:
        tower.activate(locale)
    try:
        return _build_legend()
    finally:
        tower.activate(old_locale)


def _build_legend():
    _legend = {
        BAD_BANGO_CODE:
            _('Mozilla received an invalid code from the payment '
              'provider (Bango) when processing the payment'),
        BAD_ICON_KEY:
            # L10n: First argument is an example of the proper key format.
            _('An image icon key was not an object. Correct example: {0}')
            .format('{"64": "https://.../icon_64.png"}'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        BAD_JWT_ISSUER: _('No one has been registered for this JWT issuer.'),
        BAD_PRICE_POINT: _('The price point is unknown or invalid.'),
        BAD_REQUEST: _('The request to begin payment was invalid.'),
        BAD_SIM_RESULT:
            _('The requested payment simulation result is not supported.'),
        BANGO_ERROR:
            _('The payment provider (Bango) returned an error while '
              'processing the payment'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        EXPIRED_JWT: _('The JWT has expired.'),
        INTERNAL_TIMEOUT: _('An internal web request timed out.'),
        INVALID_JWT:
            # L10n: JWT stands for JSON Web Token and does not need to be
            # localized.
            _('The JWT signature is invalid or the JWT is malformed.'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        INVALID_JWT_OBJ: _('The JWT did not decode to a JSON object.'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        JWT_DECODE_ERR: _('Error decoding JWT.'),
        LOGIN_TIMEOUT: _('The system timed out while trying to log in.'),
        LOGOUT_TIMEOUT: _('The system timed out while trying to log out.'),
        # L10n: 'postback' is a term that means a URL accepting HTTP posts.
        MALFORMED_URL: _('A URL is malformed. This could be a postback '
                         'URL or an icon URL.'),
        NO_ACTIVE_TRANS: _('The transaction ID was missing from the session '
                           'when processing a payment return.'),
        NO_DEFAULT_LOC:
            # L10n: First and second arguements are the names of keys.
            _('If {0} is defined, then you must also define {1}.')
            .format('locales', 'defaultLocale'),
        NO_SIM_REASON:
            # L10n: First argument is the name of the key, 'reason'.
            _("The requested chargeback simulation is missing "
              "the key '{0}'.").format('reason'),
        NOTICE_ERROR: _('The notification service responded with an '
                        'error while verifying the payment notice'),
        PAY_DISABLED: _('Payments are temporarily disabled'),
        RESOURCE_MODIFIED:
            _('The resource has been modified within the timing of the '
              'previous request. The action should be performed again.'),
        SIM_DISABLED: _('Payment simulations are disabled at this time.'),
        SIM_ONLY_KEY:
            _('This payment key can only be used to simulate purchases.'),
        TRANS_ENDED:
            _('The purchase cannot be completed because the current '
              'transaction has already ended.'),
        TRANS_TIMEOUT:
            _('The system timed out while waiting for a transaction '
              'to start.'),
        UNSUPPORTED_PAY:
            _('The payment method or price point is not supported for this '
              'region or operator.'),
        USER_CANCELLED: _('The user cancelled the payment.'),
    }

    # Define all short field too long errors.
    for field, key in SHORT_FIELD_TOO_LONG_CODE.iteritems():
        # L10n: First argument is the name of a key. Second
        # argument is a number.
        _legend[key] = _('The value for key "{0}" exceeds the maximum '
                         'length of {1}').format(
                                field, settings.SHORT_FIELD_MAX_LENGTH)

    return _legend
