import hashlib
import re

from django.conf import settings
from django.core.exceptions import PermissionDenied

from lib.solitude.api import client


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
    Given an email returns the hash of the email for this site. This will be
    consistent for each email for this site and can be used as the uuid in
    solitude. Because the leakage of the email is more of a privacy concern
    than a security concern, we are just doing a simple sha1 hash.

    :email: the email to hash.
    """
    if not isinstance(email, basestring):
        raise ValueError('get_uuid requires a string or unicode')
    hashed = hashlib.sha1()
    hashed.update(email)
    return '%s:%s' % (settings.DOMAIN, hashed.hexdigest())


def get_user(request):
    try:
        return request.session.get('uuid')
    except KeyError:
        raise KeyError('Attempt to access user without it being set, '
                       'did you use the user_verified decorator?')


def set_user(request, email):
    if not check_whitelist(email):
        raise PermissionDenied

    uuid = get_uuid(email)
    request.session['uuid'] = uuid
    # This is only used by navigator.id.watch()
    request.session['logged_in_user'] = email
    return update_session(request, uuid)


def update_session(request, uuid):
    buyer = client.get_buyer(uuid)
    set_user_has_pin(request, buyer.get('pin', False))
    set_user_has_confirmed_pin(request, buyer.get('pin_confirmed', False))
    set_user_reset_pin(request, buyer.get('needs_pin_reset', False))
    set_user_has_new_pin(request, buyer.get('new_pin', False))
    request.session['uuid_pin_was_locked'] = buyer.get('pin_was_locked_out',
                                                       False)
    request.session['uuid_pin_is_locked'] = buyer.get('pin_is_locked_out',
                                                      False)
    return uuid


def set_user_has_pin(request, has_pin):
    request.session['uuid_has_pin'] = has_pin


def set_user_has_confirmed_pin(request, has_confirmed_pin):
    request.session['uuid_has_confirmed_pin'] = has_confirmed_pin


def set_user_reset_pin(request, reset_pin):
    request.session['uuid_needs_pin_reset'] = reset_pin


def set_user_has_new_pin(request, has_new_pin):
    request.session['uuid_has_new_pin'] = has_new_pin
