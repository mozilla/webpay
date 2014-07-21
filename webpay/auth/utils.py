import hashlib
import hmac
import re

from django.conf import settings
from django.core.exceptions import PermissionDenied

from lib.solitude.api import client
from webpay.base.logger import getLogger

log = getLogger('w.auth')


def check_whitelist(email):
    whitelist = settings.USER_WHITELIST

    if not whitelist:
        return True

    for email_re in whitelist:
        if re.match(email_re, email):
            return True

    return False


def get_uuid(email):
    """
    Given an email returns an email token for this site. This will be
    consistent for each email for this site and can be used as the uuid in
    solitude. The email is protected by HMAC for privacy purposes.

    :email: the email to tokenize.
    """
    if not settings.DEBUG and not settings.UUID_HMAC_KEY:
        raise EnvironmentError('UUID_HMAC_KEY setting cannot be empty in '
                               'production')
    if not isinstance(email, basestring):
        raise ValueError('get_uuid requires a string or unicode')
    if isinstance(email, unicode):
        # Emails should always be UTF8 compatible but let's cope
        # with it if not.
        email = email.encode('utf8', 'replace')
    uid = hmac.new(settings.UUID_HMAC_KEY, email, hashlib.sha256).hexdigest()
    return '%s:%s' % (settings.DOMAIN, uid)


def get_user(request):
    try:
        return request.session.get('uuid')
    except KeyError:
        raise KeyError('Attempt to access user without it being set, '
                       'did you use the user_verified decorator?')


def set_user(request, email):
    if not check_whitelist(email):
        log.warning('Whitelist denied access to: {0}'.format(email))
        raise PermissionDenied

    uuid = get_uuid(email)
    new_uuid = request.session.get('uuid') != uuid
    request.session['uuid'] = uuid
    # This is only used by navigator.id.watch()
    request.session['logged_in_user'] = email

    buyer = client.get_buyer(uuid)
    if not buyer:
        buyer = client.create_buyer(uuid, email)

    return update_session(request, uuid, new_uuid, email, buyer=buyer)


def update_session(request, uuid, new_uuid, email, buyer=None):
    buyer = buyer or client.get_buyer(uuid)

    # Some buyers may not have email set
    # We must update them to store their email
    # If all buyers have emails set then this can
    # be safely removed
    if not buyer.get('email', None):
        client.update_buyer(uuid, email=email)

    set_user_has_pin(request, buyer.get('pin', False))
    set_user_has_confirmed_pin(request, buyer.get('pin_confirmed', False))
    set_user_reset_pin(request, buyer.get('needs_pin_reset', False))
    set_user_has_new_pin(request, buyer.get('new_pin', False))
    request.session['uuid_pin_was_locked'] = buyer.get('pin_was_locked_out',
                                                       False)
    request.session['uuid_pin_is_locked'] = buyer.get('pin_is_locked_out',
                                                      False)
    if new_uuid:
        request.session['last_pin_success'] = None
    return uuid


def set_user_has_pin(request, has_pin):
    request.session['uuid_has_pin'] = has_pin


def set_user_has_confirmed_pin(request, has_confirmed_pin):
    request.session['uuid_has_confirmed_pin'] = has_confirmed_pin


def set_user_reset_pin(request, reset_pin):
    request.session['uuid_needs_pin_reset'] = reset_pin


def set_user_has_new_pin(request, has_new_pin):
    request.session['uuid_has_new_pin'] = has_new_pin
