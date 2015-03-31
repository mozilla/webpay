from django.conf import settings
from django.utils import translation

import tower
from tower import ugettext as _


# Some of these codes are only referenced
# in SPA: https://github.com/mozilla/spartacus/ .

BAD_BANGO_CODE = 'BAD_BANGO_CODE'
BAD_ICON_KEY = 'BAD_ICON_KEY'
BAD_JWT_ISSUER = 'BAD_JWT_ISSUER'
BAD_PRICE_POINT = 'BAD_PRICE_POINT'
BAD_REQUEST = 'BAD_REQUEST'
BAD_SIM_RESULT = 'BAD_SIM_RESULT'
BANGO_ERROR = 'BANGO_ERROR'
BUYER_NOT_CONFIGURED = 'BUYER_NOT_CONFIGURED'
BUYER_UUID_ALREADY_EXISTS = 'BUYER_UUID_ALREADY_EXISTS'
EXPIRED_JWT = 'EXPIRED_JWT'
FIELD_REQUIRED = 'FIELD_REQUIRED'
EXT_ERROR = 'EXT_ERROR'
FXA_DENIED = 'FXA_DENIED'
FXA_FAILED = 'FXA_FAILED'
FXA_TIMEOUT = 'FXA_TIMEOUT'
INTERNAL_TIMEOUT = 'INTERNAL_TIMEOUT'
INVALID_JWT = 'INVALID_JWT'
INVALID_JWT_OBJ = 'INVALID_JWT_OBJ'
INVALID_PIN_REAUTH = 'INVALID_PIN_REAUTH'
INVALID_REDIR_URL = 'INVALID_REDIR_URL'
JWT_DECODE_ERR = 'JWT_DECODE_ERR'
LOGIN_TIMEOUT = 'LOGIN_TIMEOUT'
LOGOUT_TIMEOUT = 'LOGOUT_TIMEOUT'
LOGOUT_URL_MISSING = 'LOGOUT_URL_MISSING'
MALFORMED_URL = 'MALFORMED_URL'
MISSING_JWT = 'MISSING_JWT'
MISSING_ERROR_CODE = 'MISSING_ERROR_CODE'
NO_ACTIVE_TRANS = 'NO_ACTIVE_TRANS'
NO_DEFAULT_LOC = 'NO_DEFAULT_LOC'
NO_PAY_FAILED_FUNC = 'NO_PAY_FAILED_FUNC'
NO_PAY_SUCCESS_FUNC = 'NO_PAY_SUCCESS_FUNC'
NO_PUBLICID_IN_JWT = 'NO_PUBLICID_IN_JWT'
NO_SIM_REASON = 'NO_SIM_REASON'
NO_VALID_SELLER = 'NO_VALID_SELLER'
NOTICE_ERROR = 'NOTICE_ERROR'
NOTICE_EXCEPTION = 'NOTICE_EXCEPTION'
PAY_DISABLED = 'PAY_DISABLED'
PIN_4_NUMBERS_LONG = 'PIN_4_NUMBERS_LONG'
PIN_ALREADY_CREATED = 'PIN_ALREADY_CREATED'
PIN_ONLY_NUMBERS = 'PIN_ONLY_NUMBERS'
PIN_STATE_ERROR = 'PIN_STATE_ERROR'
PIN_STATE_TIMEOUT = 'PIN_STATE_TIMEOUT'
PROVIDER_LOGOUT_FAIL = 'PROVIDER_LOGOUT_FAIL'
REAUTH_LOGOUT_ERROR = 'REAUTH_LOGOUT_ERROR'
RESOURCE_MODIFIED = 'RESOURCE_MODIFIED'
REVERIFY_DENIED = 'REVERIFY_DENIED'
REVERIFY_FAILED = 'REVERIFY_FAILED'
REVERIFY_MISSING_PROVIDER = 'REVERIFY_MISSING_PROVIDER'
REVERIFY_MISSING_URL = 'REVERIFY_MISSING_URL'
REVERIFY_TIMEOUT = 'REVERIFY_TIMEOUT'
SELLER_NOT_CONFIGURED = 'SELLER_NOT_CONFIGURED'
SIM_DISABLED = 'SIM_DISABLED'
SIM_ONLY_KEY = 'SIM_ONLY_KEY'
SIMULATE_FAIL = 'SIMULATE_FAIL'
SIMULATE_TIMEOUT = 'SIMULATE_TIMEOUT'
STATUS_COMPLETE_UNDEF = 'STATUS_COMPLETE_UNDEF'
STATUS_PENDING_UNDEF = 'STATUS_PENDING_UNDEF'
TRANS_CONFIG_FAILED = 'TRANS_CONFIG_FAILED'
TRANS_ENDED = 'TRANS_ENDED'
TRANS_EXPIRED = 'TRANS_EXPIRED'
TRANS_MISSING = 'TRANS_MISSING'
TRANS_TIMEOUT = 'TRANS_TIMEOUT'
UNEXPECTED_ERROR = 'UNEXPECTED_ERROR'
UNEXPECTED_STATE = 'UNEXPECTED_STATE'
UNSUPPORTED_PAY = 'UNSUPPORTED_PAY'
# This string is used to determine the message on Marketplace;
# change it at your peril.
USER_CANCELLED = 'USER_CANCELLED'
USER_HASH_UNSET = 'USER_HASH_UNSET'
VERIFY_DENIED = 'VERIFY_DENIED'
VERIFY_FAILED = 'VERIFY_FAILED'
VERIFY_MISSING_PROVIDER = 'VERIFY_MISSING_PROVIDER'
VERIFY_MISSING_URL = 'VERIFY_MISSING_URL'
VERIFY_TIMEOUT = 'VERIFY_TIMEOUT'
WAIT_URL_NOT_SET = 'WAIT_URL_NOT_SET'
WRONG_PIN = 'WRONG_PIN'

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


class DevMessage(Exception):
    """
    A catchable developer message exception.
    """
    def __init__(self, msg_code):
        self.code = msg_code
        super(Exception, self).__init__('Developer message: {msg}'
                                        .format(msg=msg_code))


def _build_legend():
    _legend = {
        BAD_BANGO_CODE: _(
            'Mozilla received an invalid code from the payment '
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
        BUYER_UUID_ALREADY_EXISTS:
            _('Buyer with this UUID already exists.'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        EXPIRED_JWT: _('The JWT has expired.'),
        EXT_ERROR:
            _('The external payment processor returned an error while '
              'handling the payment'),
        FIELD_REQUIRED: _('This field is required.'),
        FXA_DENIED: _('Permission denied to verify the user.'),
        FXA_FAILED: _('Verifying the user failed.'),
        FXA_TIMEOUT:
            _('The request to the server timed out during verification.'),
        INTERNAL_TIMEOUT: _('An internal web request timed out.'),
        INVALID_JWT:
            # L10n: JWT stands for JSON Web Token and does not need to be
            # localized.
            _('The JWT signature is invalid or the JWT is malformed.'),
        INVALID_PIN_REAUTH:
            _('The user account was not re-authenticated correctly for '
              'a PIN reset.'),
        INVALID_REDIR_URL: _('The redirect URL given is not valid.'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        INVALID_JWT_OBJ: _('The JWT did not decode to a JSON object.'),
        # L10n: JWT stands for JSON Web Token and does not need to be
        # localized.
        JWT_DECODE_ERR: _('Error decoding JWT.'),
        LOGIN_TIMEOUT: _('The system timed out while trying to log in.'),
        LOGOUT_TIMEOUT: _('The system timed out while trying to log out.'),
        LOGOUT_URL_MISSING: _('The logout URL is missing from configuration.'),
        # L10n: 'postback' is a term that means a URL accepting HTTP posts.
        MALFORMED_URL: _('A URL is malformed. This could be a postback '
                         'URL or an icon URL.'),
        MISSING_JWT: _('The JWT signature is missing or invalid.'),
        MISSING_ERROR_CODE:
            _('An error code was expected but was not supplied.'),
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
        NO_PAY_FAILED_FUNC:
            # L10n: First argument is the name of a function.
            _('{0} function is undefined.').format('paymentFailed'),
        NO_PAY_SUCCESS_FUNC:
            # L10n: First argument is the name of a function.
            _('{0} function is undefined').format('paymentSuccess'),
        NOTICE_ERROR: _('The notification service responded with an '
                        'error while verifying the payment notice'),
        NOTICE_EXCEPTION: _('The notification service raised an '
                            'unexpected exception while verifying the '
                            'payment notice'),
        PAY_DISABLED: _('Payments are temporarily disabled.'),
        PIN_4_NUMBERS_LONG: _('PIN must be exactly 4 numbers long'),
        PIN_ALREADY_CREATED:
            _('The user cannot create a PIN because they already have a PIN.'),
        PIN_ONLY_NUMBERS: _('PIN must be exactly 4 numbers long'),
        PIN_STATE_ERROR:
            _('An unexpected error occurred while fetching data.'),
        PIN_STATE_TIMEOUT: _('The request timed out fetching data.'),
        PROVIDER_LOGOUT_FAIL:
            _('Failed to log out of the payment provider.'),
        REAUTH_LOGOUT_ERROR: _('An error occurred while trying to log out.'),
        RESOURCE_MODIFIED:
            _('The resource has been modified within the timing of the '
              'previous request. The action should be performed again.'),
        REVERIFY_DENIED: _('Permission denied to re-verify the user.'),
        REVERIFY_FAILED: _('Re-verifying the user failed.'),
        REVERIFY_MISSING_PROVIDER: _('The payment provider does not exist'),
        REVERIFY_MISSING_URL:
            _('The re-verification URL is missing from configuration.'),
        REVERIFY_TIMEOUT:
            _('The request to the server timed out during re-verification.'),
        SIM_DISABLED: _('Payment simulations are disabled at this time.'),
        SIM_ONLY_KEY:
            _('This payment key can only be used to simulate purchases.'),
        SIMULATE_FAIL: _('Failed to simulate a payment.'),
        SIMULATE_TIMEOUT: _('The request to simulate a payment timed out.'),
        STATUS_COMPLETE_UNDEF:
            _('Status attributes are not configured correctly.'),
        STATUS_PENDING_UNDEF:
            _('Status attributes are not configured correctly'),
        TRANS_CONFIG_FAILED:
            _('The configuration of the payment transaction failed.'),
        TRANS_ENDED:
            _('The purchase cannot be completed because the current '
              'transaction has already ended.'),
        TRANS_MISSING: _('No transaction ID could be found.'),
        TRANS_TIMEOUT:
            _('The system timed out while waiting for a transaction '
              'to start.'),
        UNEXPECTED_ERROR: _('An unexpected error occurred.'),
        UNEXPECTED_STATE: _('An unexpected error occurred.'),
        UNSUPPORTED_PAY:
            _('The payment method or price point is not supported for this '
              'region or operator.'),
        USER_CANCELLED: _('The user cancelled the payment.'),
        # L10n: First argument is the name of a var, 'user_hash'. The second
        # argument is the name of an event, 'onLogin'. The third argument
        # is the name of an event, 'onReady'.
        USER_HASH_UNSET:
            _('The app failed to set the {0} when handling {1}/{2} '
              'Persona callbacks').format('user_hash', 'onLogin', 'onReady'),
        VERIFY_DENIED: _('Permission denied to verify the user.'),
        VERIFY_FAILED: _('Verifying the user failed.'),
        VERIFY_MISSING_PROVIDER: _('The payment provider does not exist'),
        VERIFY_MISSING_URL:
            _('The verification URL is missing from configuration.'),
        VERIFY_TIMEOUT:
            _('The request to the server timed out during verification.'),
        WAIT_URL_NOT_SET: _('The wait URL is missing from configration.'),
        WRONG_PIN: _('The user entered the wrong PIN.'),
    }

    # Define all short field too long errors.
    for field, key in SHORT_FIELD_TOO_LONG_CODE.iteritems():
        # L10n: First argument is the name of a key. Second
        # argument is a number.
        _legend[key] = _('The value for key "{0}" exceeds the maximum '
                         'length of {1}').format(
                                field, settings.SHORT_FIELD_MAX_LENGTH)

    return _legend
